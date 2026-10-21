include $(TOPDIR)/rules.mk

PKG_NAME:=ckb01-oem-tools
PKG_VERSION:=2026.10.21
PKG_RELEASE:=1
PKG_LICENSE:=Proprietary
PKG_BUILD_DIR:=$(BUILD_DIR)/$(PKG_NAME)

include $(INCLUDE_DIR)/package.mk

# Preserve the original runtime hashes and the ARMv7 payload in this AArch64 package.
RSTRIP:=:
STRIP:=:

define Package/ckb01-oem-tools
  SECTION:=utils
  CATEGORY:=Utilities
  TITLE:=CKB01 original SDX55 command/file client and reversible ADB management
  DEPENDS:=@TARGET_qualcommax_ipq807x +ckb01-modem +adb +coreutils-timeout +jsonfilter +ip-full
endef

define Package/ckb01-oem-tools/description
 The original IPQ oatprsync client runs with a private OEM musl/runtime.
 SDX55 ADB is enabled on request using files in module RAM and can restore
 the original adbd service and GPIO92 state. No automatic module reset.
endef

define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)/runtime
	tar -xzf ./vendor/runtime.tar.gz -C $(PKG_BUILD_DIR)/runtime
endef

define Build/Compile
endef

define Package/ckb01-oem-tools/install
	$(INSTALL_DIR) $(1)/usr/bin $(1)/usr/sbin $(1)/lib/functions $(1)/usr/lib/ckb01-oem/runtime $(1)/usr/share/ckb01-oem
	$(CP) $(PKG_BUILD_DIR)/runtime/. $(1)/usr/lib/ckb01-oem/runtime/
	$(INSTALL_BIN) ./files/oatprsync $(1)/usr/bin/oatprsync
	$(INSTALL_BIN) ./files/ckb01-oem $(1)/usr/sbin/ckb01-oem
	$(INSTALL_BIN) ./files/ckb01-adb $(1)/usr/sbin/ckb01-adb
	$(INSTALL_DATA) ./files/ckb01-oem.sh $(1)/lib/functions/ckb01-oem.sh
	$(INSTALL_DATA) ./files/adb-control.sh $(1)/usr/lib/ckb01-oem/adb-control.sh
	$(INSTALL_DATA) ./payload/adb-tcp-property.so $(1)/usr/share/ckb01-oem/adb-tcp-property.so
	$(INSTALL_DATA) ./payload/provenance.json $(1)/usr/share/ckb01-oem/adb-payload.json
	$(INSTALL_DATA) ./vendor/provenance.json $(1)/usr/share/ckb01-oem/runtime-provenance.json
endef

$(eval $(call BuildPackage,ckb01-oem-tools))
