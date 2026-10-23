include $(TOPDIR)/rules.mk
PKG_NAME:=ckb01-edl
PKG_VERSION:=2026.10.23
PKG_RELEASE:=1
PKG_LICENSE:=BSD-3-Clause
PKG_BUILD_DIR:=$(BUILD_DIR)/$(PKG_NAME)
include $(INCLUDE_DIR)/package.mk
# The signed ARM programmer must remain byte-identical in this AArch64 package.
RSTRIP:=:
STRIP:=:
define Package/ckb01-edl
  SECTION:=utils
  CATEGORY:=Utilities
  TITLE:=CKB01 manual PCIe EDL and read-only EFS maintenance
  DEPENDS:=@TARGET_qualcommax_ipq807x +ckb01-oem-tools +libxml2 +libjson-c
endef
define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
	$(CP) ./src/* $(PKG_BUILD_DIR)/
endef
define Build/Compile
	$(TARGET_CC) $(TARGET_CFLAGS) $(TARGET_CPPFLAGS) -std=gnu11 -Wall -Wextra \
		-I$(STAGING_DIR)/usr/include/libxml2 $(PKG_BUILD_DIR)/*.c \
		-o $(PKG_BUILD_DIR)/ckb01-firehose-read $(TARGET_LDFLAGS) -lxml2 -ljson-c
endef
define Package/ckb01-edl/install
	$(INSTALL_DIR) $(1)/usr/sbin $(1)/usr/libexec $(1)/etc/modules.d $(1)/usr/share/ckb01-edl $(1)/lib/firmware/qcom/ckb01
	$(INSTALL_BIN) ./files/ckb01-edl $(1)/usr/sbin/
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/ckb01-firehose-read $(1)/usr/libexec/
	$(INSTALL_DATA) ./files/ckb01-edl.modules $(1)/etc/modules.d/29-ckb01-edl
	$(INSTALL_DATA) ./files/maintenance $(1)/etc/ckb01-maintenance
	$(INSTALL_DATA) ./firmware/prog_firehose_sdx55.mbn $(1)/lib/firmware/qcom/ckb01/
	$(INSTALL_DATA) ./firmware/provenance.json $(1)/usr/share/ckb01-edl/
endef
$(eval $(call BuildPackage,ckb01-edl))
