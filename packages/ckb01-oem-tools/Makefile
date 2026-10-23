include $(TOPDIR)/rules.mk

PKG_NAME:=ckb01-oem-tools
PKG_VERSION:=2026.10.21
PKG_RELEASE:=2
PKG_LICENSE:=Proprietary
PKG_BUILD_DIR:=$(BUILD_DIR)/$(PKG_NAME)

include $(INCLUDE_DIR)/package.mk

# Preserve the original runtime hashes and the ARMv7 payload in this AArch64 package.
RSTRIP:=:
STRIP:=:

define Package/ckb01-oem-tools
  SECTION:=utils
  CATEGORY:=Utilities
  TITLE:=CKB01 original SDX55 command/file client and reversible ADB/DIAG management
  DEPENDS:=@TARGET_qualcommax_ipq807x +ckb01-modem +adb +coreutils-timeout +jsonfilter +ip-full
endef

define Package/ckb01-oem-tools/description
 The original IPQ oatprsync client runs with a private OEM musl/runtime.
 SDX55 ADB is enabled on request using files in module RAM and can restore
 the original adbd service and GPIO92 state. PCIe DIAG is enabled at boot
 using the module OEM routing owner, with a read-only EFS client. No module reset.
endef

define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)/runtime
	$(CP) ./src/diag_efs_read.c $(PKG_BUILD_DIR)/
	tar -xzf ./vendor/runtime.tar.gz -C $(PKG_BUILD_DIR)/runtime
endef

define Build/Compile
	$(TARGET_CC) $(TARGET_CFLAGS) $(TARGET_CPPFLAGS) -Wall -Wextra -pthread \
		$(PKG_BUILD_DIR)/diag_efs_read.c -o $(PKG_BUILD_DIR)/ckb01-diag-reader $(TARGET_LDFLAGS)
endef

define Package/ckb01-oem-tools/install
	$(INSTALL_DIR) $(1)/usr/bin $(1)/usr/sbin $(1)/lib/functions $(1)/usr/lib/ckb01-oem/runtime $(1)/usr/share/ckb01-oem $(1)/usr/libexec $(1)/etc/init.d $(1)/etc/rc.d
	$(CP) $(PKG_BUILD_DIR)/runtime/. $(1)/usr/lib/ckb01-oem/runtime/
	$(INSTALL_BIN) ./files/oatprsync $(1)/usr/bin/oatprsync
	$(INSTALL_BIN) ./files/ckb01-oem $(1)/usr/sbin/ckb01-oem
	$(INSTALL_BIN) ./files/ckb01-adb $(1)/usr/sbin/ckb01-adb
	$(INSTALL_BIN) ./files/ckb01-diag-efs $(1)/usr/sbin/ckb01-diag-efs
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/ckb01-diag-reader $(1)/usr/libexec/ckb01-diag-reader
	$(INSTALL_DATA) ./files/diag-route-control.sh $(1)/usr/lib/ckb01-oem/diag-route-control.sh
	$(INSTALL_BIN) ./files/ckb01-diag-route-init $(1)/etc/init.d/ckb01-diag-route
	$(LN) ../init.d/ckb01-diag-route $(1)/etc/rc.d/S97ckb01-diag-route
	$(LN) ../init.d/ckb01-diag-route $(1)/etc/rc.d/K10ckb01-diag-route
	$(INSTALL_DATA) ./files/ckb01-oem.sh $(1)/lib/functions/ckb01-oem.sh
	$(INSTALL_DATA) ./files/adb-control.sh $(1)/usr/lib/ckb01-oem/adb-control.sh
	$(INSTALL_DATA) ./payload/adb-tcp-property.so $(1)/usr/share/ckb01-oem/adb-tcp-property.so
	$(INSTALL_DATA) ./payload/provenance.json $(1)/usr/share/ckb01-oem/adb-payload.json
	$(INSTALL_DATA) ./vendor/provenance.json $(1)/usr/share/ckb01-oem/runtime-provenance.json
endef

$(eval $(call BuildPackage,ckb01-oem-tools))
