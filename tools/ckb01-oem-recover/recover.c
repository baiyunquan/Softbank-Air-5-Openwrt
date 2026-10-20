/* SPDX-License-Identifier: GPL-2.0-only
 * Standalone recovery for OEM IPQ aarch64 / SDX55 armv7 Linux.
 * No libc/dependencies. Only PDC selected GET/SET/ACTIVATE for the original
 * ID read from our durable JSON backup. No firmware load, NV, or MHI reset.
 */
typedef unsigned int u32;
typedef unsigned short u16;
typedef unsigned char u8;
#if defined(__aarch64__)
#define NR_READ 63
#define NR_WRITE 64
#define NR_CLOSE 57
#define NR_SOCKET 198
#define NR_BIND 200
#define NR_NAME 204
#define NR_SEND 206
#define NR_RECV 207
#define NR_EXIT 93
static long call(long n,long a,long b,long c,long d,long e,long f) {
 register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c,x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f,x8 __asm__("x8")=n;
 __asm__ volatile("svc 0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8):"memory","cc"); return x0;
}
static long open_file(const char*p){return call(56,-100,(long)p,0,0,0,0);}
struct timespec {long seconds,nanos;};
struct pollfd {int fd;short events,revents;};
static long poll_one(struct pollfd*p,int ms){struct timespec t={ms/1000,(ms%1000)*1000000};return call(73,(long)p,1,(long)&t,0,0,0);}
#else
#define NR_READ 3
#define NR_WRITE 4
#define NR_CLOSE 6
#define NR_SOCKET 281
#define NR_BIND 282
#define NR_NAME 286
#define NR_SEND 290
#define NR_RECV 292
#define NR_EXIT 1
static long call(long n,long a,long b,long c,long d,long e,long f) {
 register long r0 __asm__("r0")=a,r1 __asm__("r1")=b,r2 __asm__("r2")=c,r3 __asm__("r3")=d,r4 __asm__("r4")=e,r5 __asm__("r5")=f,r7 __asm__("r7")=n;
 __asm__ volatile("svc 0":"+r"(r0):"r"(r1),"r"(r2),"r"(r3),"r"(r4),"r"(r5),"r"(r7):"memory","cc"); return r0;
}
static long open_file(const char*p){return call(5,(long)p,0,0,0,0,0);}
struct pollfd {int fd;short events,revents;};
static long poll_one(struct pollfd*p,int ms){return call(168,(long)p,1,ms,0,0,0);}
#endif
void *memset(void*d,int v,unsigned long n){volatile u8*p=d;while(n--)*p++=v;return d;}
void *memcpy(void*d,const void*s,unsigned long n){u8*p=d;const u8*q=s;while(n--)*p++=*q++;return d;}
static u32 length(const char*s){u32 n=0;while(s[n])n++;return n;}
static void text(const char*s){call(NR_WRITE,1,(long)s,length(s),0,0,0);}
static char *find(char*s,const char*needle){for(;*s;s++){u32 i=0;while(needle[i]&&s[i]&&needle[i]==s[i])i++;if(!needle[i])return s;}return 0;}
static u16 get16(const u8*p){return p[0]|p[1]<<8;}
static u32 get32(const u8*p){return get16(p)|(u32)get16(p+2)<<16;}
static void put32(u8*p,u32 v){for(u32 i=0;i<4;i++)p[i]=v>>(8*i);}
static void dump(const u8*p,u32 n){char hex[8194];const char*d="0123456789abcdef";if(n>4096)return;for(u32 i=0;i<n;i++){hex[2*i]=d[p[i]>>4];hex[2*i+1]=d[p[i]&15];}hex[2*n]='\n';hex[2*n+1]=0;text(hex);}
struct addr {u16 family,pad;u32 node,port;};
static long socket_qrtr(struct addr*local){long fd=call(NR_SOCKET,42,2,0,0,0,0);u32 len=12;if(fd<0||call(NR_NAME,fd,(long)local,(long)&len,0,0,0)<0)return -1;local->port=0;if(call(NR_BIND,fd,(long)local,12,0,0,0)<0)return -1;return fd;}
static long receive(long fd,u8*buf,struct addr*from,int timeout){struct pollfd p={(int)fd,1,0};if(poll_one(&p,timeout)<=0)return -1;u32 n=12;return call(NR_RECV,fd,(long)buf,4096,0,(long)from,(long)&n);}
static int lookup(long fd,struct addr*local,struct addr*peer){u8 lookup[20]={10,0,0,0,36};struct addr ctrl={42,0,local->node,0xfffffffe};if(call(NR_SEND,fd,(long)lookup,20,0,(long)&ctrl,12)!=20)return 1;u8 buf[4096];int found=0;
 for(u32 attempt=0;attempt<64;attempt++){struct addr from;long n=receive(fd,buf,&from,attempt?300:5000);if(n<0)break;if(n<20||get32(buf)!=4||get32(buf+4)!=36||!get32(buf+16))continue;struct addr candidate={42,0,get32(buf+12),get32(buf+16)};if(found&&(candidate.node!=peer->node||candidate.port!=peer->port)){text("ambiguous PDC endpoints\n");return 1;}*peer=candidate;found=1;}
 return !found;
}
/* Strictly require matching transaction response and matching token indication. */
static int pdc(long fd,struct addr*peer,u16 msg,u32 token,const u8*id,u8*active){u8 req[128]={0};req[1]=token;req[2]=token>>8;req[3]=msg;req[4]=msg>>8;u32 n=7;req[n++]=1;req[n++]=id?25:4;req[n++]=0;put32(req+n,1);n+=4;if(id){req[n++]=20;memcpy(req+n,id,20);n+=20;}req[n++]=0x10;req[n++]=4;req[n++]=0;put32(req+n,token);n+=4;req[5]=n-7;
 if(call(NR_SEND,fd,(long)req,n,0,(long)peer,12)!=n)return 1;
 int response=0,indication=0;u8 buf[4096];
 for(u32 tries=0;tries<16;tries++){struct addr from;long got=receive(fd,buf,&from,5000);if(got<0)continue;if(got<7)return 1;if(from.node!=peer->node||from.port!=peer->port||get16(buf+3)!=msg||get16(buf+5)!=(u32)got-7)continue;
  int result=-1,have_token=0;u8 selected[20]={0};int has_active=0;
  for(u32 i=7;i<(u32)got;){if((u32)got-i<3)return 1;u32 t=buf[i],len=get16(buf+i+1);i+=3;if(len>(u32)got-i)return 1;u8*v=buf+i;i+=len;if(buf[0]==2&&t==2&&len==4)result=get16(v)?get16(v+2):0;if(buf[0]==4&&t==1&&len==2)result=get16(v);if(t==0x10&&len==4&&get32(v)==token)have_token=1;if(buf[0]==4&&msg==0x22&&t==0x11&&len==21&&v[0]==20){memcpy(selected,v+1,20);has_active=1;}}
  if(buf[0]==2&&get16(buf+1)==(token&65535)){dump(buf,got);if(result!=0)return 1;response=1;}
  if(buf[0]==4&&have_token){dump(buf,got);if(result!=0||(msg==0x22&&!has_active))return 1;if(active)memcpy(active,selected,20);indication=1;}
  if(response&&indication)return 0;
 }return 1;
}
int recover_main(long*sp){char**argv=(char**)(sp+1);if(*sp!=2){text("usage: ckb01-oem-recover ORIGINAL-PROFILE.json\n");return 2;}static char json[65537];long file=open_file(argv[1]);if(file<0)return 2;long n=call(NR_READ,file,(long)json,65536,0,0,0);call(NR_CLOSE,file,0,0,0,0,0);if(n<=0||n>=65536)return 2;json[n]=0;char*s=find(json,"\"original_selected\"");if(!s||(s=find(s,"\"active_id\""))==0||(s=find(s,":"))==0)return 2;s++;while(*s==' '||*s=='\n'||*s=='\t')s++;if(*s++!='"')return 2;u8 target[20],active[20];for(u32 i=0;i<20;i++){u32 v=0;for(u32 j=0;j<2;j++){char c=*s++;if(c>='0'&&c<='9')v=v*16+c-'0';else if(c>='a'&&c<='f')v=v*16+c-'a'+10;else return 2;}target[i]=v;}if(*s!='"')return 2;
 struct addr local={42,0,0,0},peer={42,0,0,0};long fd=socket_qrtr(&local);if(fd<0||lookup(fd,&local,&peer)){text("PDC QRTR discovery failed\n");return 3;}
 if(pdc(fd,&peer,0x22,1,0,active))return 3;int same=1;for(u32 i=0;i<20;i++)if(target[i]!=active[i])same=0;if(same){text("original PDC already active\n");return 0;}
 if(pdc(fd,&peer,0x23,2,target,0)||pdc(fd,&peer,0x27,3,0,0)||pdc(fd,&peer,0x22,4,0,active))return 3;for(u32 i=0;i<20;i++)if(active[i]!=target[i])return 3;text("original PDC restored and active ID confirmed; verify NAS after cold boot\n");return 0;
}
#if defined(__aarch64__)
__asm__(".global _start\n_start:\nmov x0, sp\nbl recover_main\nmov x8, #93\nsvc #0\n");
#else
__asm__(".global _start\n_start:\nmov r0, sp\nbl recover_main\nmov r7, #1\nsvc #0\n");
#endif
