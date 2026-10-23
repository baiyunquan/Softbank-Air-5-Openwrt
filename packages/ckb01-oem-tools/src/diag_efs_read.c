/* Read-only DIAG EFS2 client. Protocol reference:
 * https://github.com/grmrgecko/qcdm-efs2 (309997a175f895f44908b6d2878c9c4813044f89)
 * Qualcomm diagchar ABI: Linux Foundation/LineageOS diagchar.h/core.c.
 * No EFS writes, NV writes, download-mode or modem-reset commands.
 * backup is a logical file export, NOT a physical NAND/mtd2 image.
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <fcntl.h>
#include <signal.h>
#include <pthread.h>
#include <termios.h>
#include <time.h>
#include <sys/stat.h>
#include <sys/ioctl.h>
#include <getopt.h>

#define CAP 65536
#define PATHCAP 2048
enum { HELLO=0, OPEN=2, CLOSE=3, READ=4, READLINK=7, OPENDIR=11, READDIR=12, CLOSEDIR=13, STAT=15 };
static int dev=-1, native=1, modern=1, proc=0, timeout_s=5, switched=0;
static FILE *trace, *manifest;
static pthread_t thread;
static int thread_started, fatal_link;
static pthread_mutex_t mu=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t cv=PTHREAD_COND_INITIALIZER;
static uint8_t response[CAP], want[4];
static size_t response_n, want_n;
static int waiting, rx_error, rejected;
static unsigned long rx_frames, bad_crc, skipped;
static unsigned long native_reads;
static unsigned long files_ok, files_bad, dirs_ok, links_skipped;
static unsigned long links_ok;
static unsigned long long bytes_ok;
static uint32_t rd32(const uint8_t *p) { return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static void wr32(uint8_t *p,uint32_t v) { p[0]=v;p[1]=v>>8;p[2]=v>>16;p[3]=v>>24; }
static uint16_t fcs(const uint8_t *p,size_t n) {
    uint16_t c=0xffff; size_t i; int j;
    for(i=0;i<n;i++) { c^=p[i];for(j=0;j<8;j++) c=(c>>1)^((c&1)?0x8408:0); }
    return (uint16_t)~c;
}
static void hexlog(const char *tag,const uint8_t *p,size_t n) {
    size_t i;int old;if(!trace)return;
    pthread_setcancelstate(PTHREAD_CANCEL_DISABLE,&old);flockfile(trace);
    fprintf(trace,"%s %zu ",tag,n);for(i=0;i<n;i++)fprintf(trace,"%02x",p[i]);fputc('\n',trace);fflush(trace);
    funlockfile(trace);pthread_setcancelstate(old,NULL);
}
static void delivered(const uint8_t *p,size_t n) {
    pthread_mutex_lock(&mu); rx_frames++;
    if(waiting && n>=want_n && !memcmp(p,want,want_n)) {
        if(n<=CAP) { memcpy(response,p,n);response_n=n;waiting=0;hexlog("RX",p,n);pthread_cond_signal(&cv); }
    } else if(waiting && n>=want_n+1 && (p[0]==0x13||p[0]==0x14||p[0]==0x15||p[0]==0x18||p[0]==0x42)
              && !memcmp(p+1,want,want_n)) {
        hexlog("REJECT",p,n);rejected=p[0];waiting=0;pthread_cond_signal(&cv);
    } else { skipped++; if(skipped<8)hexlog("ASYNC",p,n); }
    pthread_mutex_unlock(&mu);
}
static uint8_t frame[CAP];static size_t frame_n;static int escaped,overflow;
static void feed(const uint8_t *p,size_t n) {
    size_t i;for(i=0;i<n;i++) {
        uint8_t b=p[i];
        if(b==0x7e) {
            if(!overflow&&!escaped&&frame_n>=3) {
                uint16_t c=frame[frame_n-2]|(uint16_t)frame[frame_n-1]<<8;
                if(fcs(frame,frame_n-2)==c)delivered(frame,frame_n-2);else bad_crc++;
            }
            frame_n=0;escaped=overflow=0;continue;
        }
        if(overflow)continue;
        if(escaped) {b^=0x20;escaped=0;} else if(b==0x7d) {escaped=1;continue;}
        if(frame_n<CAP)frame[frame_n++]=b;else overflow=1;
    }
}
static void *receiver(void *unused) {
    uint8_t *b=malloc(CAP);(void)unused;
    if(!b) {pthread_mutex_lock(&mu);rx_error=ENOMEM;pthread_cond_signal(&cv);pthread_mutex_unlock(&mu);return NULL;}
    for(;;) {
        ssize_t n=read(dev,b,CAP);size_t at;uint32_t count,i;
        if(n<0&&errno==EINTR)continue;
        if(n<=0) {pthread_mutex_lock(&mu);rx_error=n<0?errno:EPIPE;pthread_cond_signal(&cv);pthread_mutex_unlock(&mu);break;}
        if(!native) {feed(b,(size_t)n);continue;}
        if(native_reads++<8)hexlog("NATIVE",b,n>128?128:(size_t)n);
        if(n<4)continue;
        if(rd32(b)==0x1000 && n>=5 && b[4]) {
            pthread_mutex_lock(&mu);rx_error=EPROTONOSUPPORT;pthread_cond_signal(&cv);pthread_mutex_unlock(&mu);break;
        }
        if(rd32(b)!=0x20 || n<8)continue; /* masks/registration notices */
        count=rd32(b+4);at=8;
        for(i=0;i<count&&at+4<=(size_t)n;i++) {
            int source=0;uint32_t len;
            if((int32_t)rd32(b+at)<0) {source=-(int32_t)rd32(b+at);at+=4;}
            if(at+4>(size_t)n)break;
            len=rd32(b+at);at+=4;if(len>(size_t)n-at)break;
            if(source==proc)feed(b+at,len);
            at+=len;
        }
    }
    free(b);return NULL;
}
static int send_request(const uint8_t *p,size_t n) {
    uint8_t b[CAP];size_t len=0,i;ssize_t w;uint16_t c;
    if(native) {
        wr32(b,0x80);len=4;if(proc) {wr32(b+len,(uint32_t)-proc);len+=4;}
        memcpy(b+len,p,n);len+=n;
        do {w=write(dev,b,len);}while(w<0&&errno==EINTR);
        /* diagchar writes return 0 on successful dispatch on some kernels. */
        if(w<0)return -1;
        if(w!=0&&(size_t)w!=len) {errno=EIO;return -1;}return 0;
    }
    c=fcs(p,n);
    for(i=0;i<n+2;i++) {
        uint8_t v=i<n?p[i]:(i==n?c&255:c>>8);
        if(v==0x7e||v==0x7d) {b[len++]=0x7d;b[len++]=v^0x20;}else b[len++]=v;
    }
    b[len++]=0x7e;
    for(i=0;i<len;) {w=write(dev,b+i,len-i);if(w<0&&errno==EINTR)continue;if(w<=0)return -1;i+=(size_t)w;}
    return 0;
}
static int txn(const uint8_t *p,size_t n,size_t keylen,size_t minlen) {
    struct timespec deadline;int e=0;
    if(fatal_link){errno=ENOTCONN;return -1;}
    pthread_mutex_lock(&mu);memcpy(want,p,keylen);want_n=keylen;waiting=1;response_n=0;rejected=0;
    hexlog("TX",p,n);pthread_mutex_unlock(&mu);
    if(send_request(p,n)<0){fatal_link=1;return -1;}
    clock_gettime(CLOCK_REALTIME,&deadline);deadline.tv_sec+=timeout_s;
    pthread_mutex_lock(&mu);
    while(waiting&&!rx_error&&e!=ETIMEDOUT) e=pthread_cond_timedwait(&cv,&mu,&deadline);
    waiting=0;
    if(rx_error) {errno=rx_error;fatal_link=1;e=-1;} else if(rejected) {
        fprintf(stderr,"DIAG rejected request: 0x%02x (not an EFS errno)\n",rejected);
        errno=rejected==0x13?EOPNOTSUPP:rejected==0x14?EINVAL:rejected==0x15?EMSGSIZE:rejected==0x18?EBUSY:EACCES;e=-1;
    }
    else if(response_n<minlen) {errno=response_n?EPROTO:ETIMEDOUT;fatal_link=1;e=-1;} else e=0;
    pthread_mutex_unlock(&mu);return e;
}
static int efs(uint16_t cmd,const void *body,size_t n,size_t minlen) {
    uint8_t p[4096];if(n>sizeof(p)-4) {errno=EMSGSIZE;return -1;}
    p[0]=0x4b;p[1]=19;p[2]=cmd;p[3]=cmd>>8;if(n)memcpy(p+4,body,n);
    return txn(p,n+4,4,minlen);
}
static int eerr(uint32_t e) {if(!e)return 0;fprintf(stderr,"EFS errno=%u\n",e);errno=e<4096?(int)e:EIO;return -1;}
static int fs_stat(const char *p,uint32_t *mode,uint32_t *size) {
    if(efs(STAT,p,strlen(p)+1,16)<0||eerr(rd32(response+4))<0)return -1;
    *mode=rd32(response+8);*size=rd32(response+12);return 0;
}
static int close_handle(int fd,int dir) {
    uint8_t b[4];wr32(b,fd);if(efs(dir?CLOSEDIR:CLOSE,b,4,8)<0)return -1;return eerr(rd32(response+4));
}
static int remote_open(const char *path) {
    uint8_t b[PATHCAP+8]={0};int f;
    if(strlen(path)>=PATHCAP){errno=ENAMETOOLONG;return -1;}
    memcpy(b+8,path,strlen(path)+1); /* flags=O_RDONLY, mode=0 */
    if(efs(OPEN,b,strlen(path)+9,12)<0||eerr(rd32(response+8))<0)return -1;
    f=(int32_t)rd32(response+4);if(f<0)errno=EBADF;return f;
}
static int fs_read(int f,uint32_t off,uint32_t need,uint8_t *out) {
    uint8_t b[12];int32_t got;
    wr32(b,f);wr32(b+4,need);wr32(b+8,off);
    if(efs(READ,b,12,20)<0||eerr(rd32(response+16))<0)return -1;
    got=(int32_t)rd32(response+12);
    if(rd32(response+4)!=(uint32_t)f||rd32(response+8)!=off||got<0||(uint32_t)got>need||(size_t)got>response_n-20) {errno=EPROTO;return -1;}
    memcpy(out,response+20,(size_t)got);return got;
}
static void record(const char *status,const char *path,unsigned long size,int error) {
    if(manifest) {fprintf(manifest,"%s\t%lu\t%d\t%s\n",status,size,error,path);fflush(manifest);}
}
static int readlink_target(const char *remote,char *target,size_t cap) {
    size_t n;
    if(efs(READLINK,remote,strlen(remote)+1,9)<0||eerr(rd32(response+4))<0)return -1;
    n=response_n-8;
    const uint8_t *end=memchr(response+8,0,n);
    if(!end||end==response+8||(size_t)(end-response-8)>=cap){errno=EPROTO;return -1;}
    n=(size_t)(end-response-8);memcpy(target,response+8,n);target[n]=0;return (int)n;
}
static int save_link(const char *remote,const char *local) {
    char target[PATHCAP],sidecar[PATHCAP+32];int n=readlink_target(remote,target,sizeof(target));
    if(n<0)return -1;
    if(snprintf(sidecar,sizeof(sidecar),"%s.symlink-target",local)>=(int)sizeof(sidecar)){errno=ENAMETOOLONG;return -1;}
    int l=open(sidecar,O_CREAT|O_EXCL|O_WRONLY|O_NOFOLLOW,0600);if(l<0)return -1;
    size_t off=0;int e=0;
    while(off<(size_t)n){ssize_t w=write(l,target+off,n-off);if(w<0&&errno==EINTR)continue;if(w<=0){e=errno?errno:EIO;break;}off+=(size_t)w;}
    if(!e&&fsync(l)<0)e=errno;
    if(close(l)<0&&!e)e=errno;
    if(e){errno=e;return -1;}
    links_ok++;record("LINK_TARGET",remote,(unsigned long)n,0);return 0;
}
static int pull(const char *remote,const char *local) {
    uint32_t mode,size,off=0,after_mode,after_size;int f=-1,l=-1,e=0;uint8_t chunk[1024];char part[PATHCAP+16];
    if(fs_stat(remote,&mode,&size)<0)return -1;
    if((mode&0170000)==0040000||(mode&0170000)==0120000) {errno=EINVAL;return -1;}
    if(snprintf(part,sizeof(part),"%s.partial",local)>=(int)sizeof(part)) {errno=ENAMETOOLONG;return -1;}
    if(access(local,F_OK)==0) {errno=EEXIST;return -1;}
    l=open(part,O_CREAT|O_EXCL|O_WRONLY|O_NOFOLLOW,0600);if(l<0)return -1;
    f=remote_open(remote);if(f<0){e=errno;goto done;}
    while(off<size) {
        uint32_t need=size-off;if(need>sizeof(chunk))need=sizeof(chunk);
        int got=fs_read(f,off,need,chunk);size_t at=0;
        if(got<=0){e=got<0?errno:EIO;goto done;}
        while(at<(size_t)got){ssize_t w=write(l,chunk+at,got-at);if(w<0&&errno==EINTR)continue;if(w<=0){e=errno?errno:EIO;goto done;}at+=(size_t)w;}
        off+=(uint32_t)got;
    }
    if(close_handle(f,0)<0){e=errno;f=-1;goto done;}f=-1;
    if(fs_stat(remote,&after_mode,&after_size)<0){e=errno;goto done;}
    if(size!=after_size||mode!=after_mode){e=ESTALE;goto done;}
    if(fsync(l)<0){e=errno;goto done;}
done:
    if(f>=0)close_handle(f,0);
    if(l>=0&&close(l)<0&&!e)e=errno;
    if(!e&&rename(part,local)<0)e=errno;
    if(e){errno=e;return -1;}
    files_ok++;bytes_ok+=size;record("FILE",remote,size,0);printf("FILE %u %s\n",size,remote);fflush(stdout);return 0;
}
struct entry {char name[1024];uint32_t type,size;};
static int directory(const char *path,struct entry **items,size_t *count) {
    uint8_t b[8];int f=-1,e=0;uint32_t seq=1;size_t cap=0;*items=NULL;*count=0;
    if(efs(OPENDIR,path,strlen(path)+1,12)<0||eerr(rd32(response+8))<0)return -1;
    f=(int32_t)rd32(response+4);if(f<0){errno=EBADF;return -1;}
    for(;;seq++) {
        uint32_t er;const uint8_t *end;
        wr32(b,f);wr32(b+4,seq);
        if(efs(READDIR,b,8,16)<0){e=errno;break;}
        if(rd32(response+4)!=(uint32_t)f||rd32(response+8)!=seq){e=EPROTO;break;}
        er=rd32(response+12);if(er){e=(int)er;break;}
        if(response_n<41){e=EPROTO;break;}
        end=memchr(response+40,0,response_n-40);if(!end){e=EPROTO;break;}
        if(end==response+40)break; /* only a zero-errno empty name is EOF */
        size_t len=(size_t)(end-(response+40));
        if(len>=sizeof((*items)[0].name)||seq>200000){e=EOVERFLOW;break;}
        if(*count==cap){cap=cap?cap*2:32;void *p=realloc(*items,cap*sizeof(**items));if(!p){e=ENOMEM;break;}*items=p;}
        struct entry *x=&(*items)[(*count)++];memcpy(x->name,response+40,len);x->name[len]=0;x->type=rd32(response+16);x->size=rd32(response+24);
    }
    if(close_handle(f,1)<0&&!e)e=errno;
    if(e){free(*items);*items=NULL;*count=0;errno=e;return -1;}return 0;
}
static int mkdirs(const char *path) {
    char b[PATHCAP];size_t i;struct stat st;
    if(strlen(path)>=sizeof(b)){errno=ENAMETOOLONG;return -1;}strcpy(b,path);
    for(i=1;;i++)if(b[i]=='/'||b[i]==0) {char c=b[i];b[i]=0;
        if(mkdir(b,0700)<0&&errno!=EEXIST)return -1;
        if(lstat(b,&st)<0||!S_ISDIR(st.st_mode)){errno=ENOTDIR;return -1;}b[i]=c;if(!c)break;
    }return 0;
}
static int valid_name(const char *s) {
    if(!s[0]||!strcmp(s,".")||!strcmp(s,"..")||strchr(s,'/'))return 0;
    for(;*s;s++)if((unsigned char)*s<32||*s==127)return 0;
    return 1;
}
static void walk(const char *remote,const char *local,int depth) {
    struct entry *list=NULL;size_t n=0,i;
    if(depth>64){files_bad++;record("DEPTH",remote,0,ELOOP);return;}
    if(mkdirs(local)<0||directory(remote,&list,&n)<0){int e=errno;files_bad++;record("DIR_ERROR",remote,0,e);fprintf(stderr,"DIR_ERROR %s: %s\n",remote,strerror(e));return;}
    dirs_ok++;record("DIR",remote,n,0);
    for(i=0;i<n;i++) {
        char r[PATHCAP],l[PATHCAP];struct entry *x=&list[i];
        if(fatal_link){record("ABORT_TRANSPORT",remote,0,ENOTCONN);break;}
        if(!strcmp(x->name,".")||!strcmp(x->name,".."))continue;
        if(!valid_name(x->name)){files_bad++;record("NAME_ERROR",remote,0,EINVAL);continue;}
        if(snprintf(r,sizeof(r),"%s%s%s",remote,!strcmp(remote,"/")?"":"/",x->name)>=(int)sizeof(r)||snprintf(l,sizeof(l),"%s/%s",local,x->name)>=(int)sizeof(l)){files_bad++;record("PATH_ERROR",remote,0,ENAMETOOLONG);continue;}
        if(x->type==1)walk(r,l,depth+1);
        else if(x->type==0||x->type==15) {if(pull(r,l)<0){int e=errno;files_bad++;record("FILE_ERROR",r,x->size,e);fprintf(stderr,"FILE_ERROR %s: %s\n",r,strerror(e));}}
        else if(x->type==2){if(save_link(r,l)<0){int e=errno;files_bad++;record("LINK_ERROR",r,0,e);fprintf(stderr,"LINK_ERROR %s: %s\n",r,strerror(e));}}
        else {links_skipped++;record("SKIP_TYPE",r,x->type,0);}
    }
    free(list);
}
static int mode_switch(int mode) {
    uint8_t param[24]={0};wr32(param,mode);
    /* ABI layouts confirmed against each OEM libdiag switch wrapper. */
    if(modern==2) {wr32(param+4,0x1f);param[8]=1;}
    else {
        wr32(param+4,0x7f);param[12]=1;wr32(param+16,(uint32_t)-22);
        /* SDX55 OEM ABI is 24 bytes: trailing local-device mask is mandatory. */
        wr32(param+20,1);
    }
    return ioctl(dev,7,modern?(void*)param:(void*)&mode);
}
static void cleanup(void) {
    if(dev<0)return;
    if(switched) {if(mode_switch(1)<0)perror("restore DIAG USB routing");switched=0;}
    if(thread_started){pthread_cancel(thread);pthread_join(thread,NULL);thread_started=0;}
    close(dev);dev=-1;
    fprintf(stderr,"rx_frames=%lu bad_crc=%lu unmatched=%lu native_reads=%lu\n",rx_frames,bad_crc,skipped,native_reads);
    if(trace){fclose(trace);trace=NULL;}
}
static void usage(const char *p) {
    fprintf(stderr,"Usage: %s [-d DEVICE] [-t hdlc|diag] [--abi old|new|qsdk] [--proc 0..9] [--timeout SEC] [--trace FILE] probe|hello|ls PATH|stat PATH|readlink PATH|pull PATH LOCAL|backup PATH DEST\n",p);
}
int main(int argc,char **argv) {
    const char *path="/dev/diag",*op;int c,result=0;uint8_t b[40];
    static const struct option opts[]={{"device",1,0,'d'},{"transport",1,0,'t'},{"abi",1,0,'a'},{"proc",1,0,'p'},{"timeout",1,0,'w'},{"trace",1,0,'l'},{"help",0,0,'h'},{0,0,0,0}};
    setvbuf(stdout,NULL,_IOLBF,0);setvbuf(stderr,NULL,_IOLBF,0);signal(SIGPIPE,SIG_IGN);
    while((c=getopt_long(argc,argv,"d:t:a:p:w:l:h",opts,NULL))!=-1) {
        switch(c) {
        case 'd':path=optarg;break;
        case 't':if(!strcmp(optarg,"diag"))native=1;else if(!strcmp(optarg,"hdlc"))native=0;else return 1;break;
        case 'a':if(!strcmp(optarg,"new"))modern=1;else if(!strcmp(optarg,"old"))modern=0;else if(!strcmp(optarg,"qsdk"))modern=2;else return 1;break;
        case 'p':proc=atoi(optarg);if(proc<0||proc>9)return 1;break;
        case 'w':timeout_s=atoi(optarg);if(timeout_s<1||timeout_s>120)return 1;break;
        case 'l':trace=fopen(optarg,"wx");if(!trace){perror("trace");return 1;}break;
        default:usage(argv[0]);return c=='h'?0:1;
        }
    }
    if(optind>=argc){usage(argv[0]);return 1;}op=argv[optind++];
    int required=(!strcmp(op,"probe")||!strcmp(op,"hello"))?0:(!strcmp(op,"ls")||!strcmp(op,"stat")||!strcmp(op,"readlink"))?1:(!strcmp(op,"pull")||!strcmp(op,"backup"))?2:-1;
    if(required<0||argc-optind!=required){usage(argv[0]);return 1;}
    if(required&& (argv[optind][0]!='/'||strlen(argv[optind])>=PATHCAP)){fprintf(stderr,"absolute EFS path required\n");return 1;}
    dev=open(path,O_RDWR|O_CLOEXEC);if(dev<0){perror(path);return 1;}atexit(cleanup);
    if(native) {
        uint16_t rem=0;int rv=ioctl(dev,32,&rem);
        fprintf(stderr,"diag ABI=%s remote-mask=0x%x ioctl32=%d selected-proc=%d\n",modern==2?"qsdk":modern?"new":"old",rem,rv,proc);
        if(proc&&!(rem&proc)){fprintf(stderr,"selected remote processor is unavailable\n");return 1;}
        int callback_proc=proc;
        if(ioctl(dev,37,&callback_proc)<0){perror("DIAG callback registration ioctl37");return 1;}
        if(mode_switch(6)<0){perror("DIAG callback logging ioctl7");return 1;}switched=1;
    } else if(isatty(dev)) {
        struct termios term;if(tcgetattr(dev,&term)<0)return 1;cfmakeraw(&term);cfsetispeed(&term,B115200);cfsetospeed(&term,B115200);term.c_cflag|=CLOCAL|CREAD;term.c_cc[VMIN]=1;term.c_cc[VTIME]=0;if(tcsetattr(dev,TCSANOW,&term)<0)return 1;
    }
    if(pthread_create(&thread,NULL,receiver,NULL)){fprintf(stderr,"receiver thread failed\n");return 1;}
    thread_started=1;
    if(!strcmp(op,"probe")) {
        b[0]=0;if(txn(b,1,1,2)<0){perror("DIAG version");return 1;}
        printf("DIAG_VERSION bytes=%zu data=",response_n);for(size_t i=0;i<response_n;i++)printf("%02x",response[i]);puts("");
    }
    for(int i=0;i<6;i++)wr32(b+i*4,0x100000);
    for(int i=6;i<9;i++)wr32(b+i*4,1);
    wr32(b+36,0xffffffff);
    if(efs(HELLO,b,40,40)<0){perror("EFS HELLO");return 1;}
    printf("EFS_HELLO version=%u max=%u min=%u features=0x%x\n",rd32(response+28),rd32(response+32),rd32(response+36),response_n>=44?rd32(response+40):0);
    if(!strcmp(op,"stat")){uint32_t m,s;if(fs_stat(argv[optind],&m,&s)<0){perror("stat");return 1;}printf("%s mode=%o size=%u\n",argv[optind],m,s);}
    else if(!strcmp(op,"readlink")){char target[PATHCAP];if(readlink_target(argv[optind],target,sizeof(target))<0){perror("readlink");return 1;}printf("%s\n",target);}
    else if(!strcmp(op,"ls")){struct entry *es=NULL;size_t n=0;if(directory(argv[optind],&es,&n)<0){perror("ls");return 1;}for(size_t i=0;i<n;i++)printf("type=%u size=%u %s\n",es[i].type,es[i].size,es[i].name);free(es);}
    else if(!strcmp(op,"pull")){if(pull(argv[optind],argv[optind+1])<0){perror("pull");return 1;}}
    else if(!strcmp(op,"backup")) {
        char meta[PATHCAP];if(mkdirs(argv[optind+1])<0){perror("destination");return 1;}
        if(snprintf(meta,sizeof(meta),"%s.manifest.tsv",argv[optind+1])>=(int)sizeof(meta))return 1;
        manifest=fopen(meta,"wx");if(!manifest){perror("manifest");return 1;}fprintf(manifest,"status\tbytes_or_type\terrno\tefs_path\n");
        walk(argv[optind],argv[optind+1],0);
        printf("SUMMARY files=%lu bytes=%llu dirs=%lu errors=%lu links=%lu skipped_types=%lu\n",files_ok,bytes_ok,dirs_ok,files_bad,links_ok,links_skipped);
        record(files_bad||links_skipped?"PARTIAL":"COMPLETE",argv[optind],files_ok,files_bad?EIO:0);fclose(manifest);result=files_bad||links_skipped?2:0;
    }
    /* Stop receiver before trace is flushed by libc at exit. */
    cleanup();return result;
}
