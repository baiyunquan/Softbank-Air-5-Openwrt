# SPDX-License-Identifier: GPL-2.0-only
include $(TOPDIR)/rules.mk
PKG_NAME:=ckb01-modem
PKG_RELEASE:=6
PKG_LICENSE:=GPL-2.0-only
PKG_BUILD_DIR:=$(BUILD_DIR)/$(PKG_NAME)
PKG_BUILD_DEPENDS:=libqmi libqrtr-glib libjson-c
include $(INCLUDE_DIR)/package.mk

define Package/ckb01-modem
  SECTION:=net
  CATEGORY:=Network
  TITLE:=OPPO CKB01 SDX55 QMI/QRTR bring-up
  DEPENDS:=+libqmi +libqrtr-glib +libjson-c +qmi-utils +kmod-rmnet +ip-full +jsonfilter +uhttpd +coreutils-timeout
endef

define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
	$(CP) ./src/* $(PKG_BUILD_DIR)/
endef

define Build/Compile
	$(TARGET_CC) $(TARGET_CFLAGS) -std=c11 -D_GNU_SOURCE -Wall -Wextra \
		$(TARGET_CPPFLAGS) `$(STAGING_DIR_HOST)/bin/pkg-config --cflags qmi-glib qrtr-glib json-c` \
		$(PKG_BUILD_DIR)/*.c -o $(PKG_BUILD_DIR)/ckb01-modem $(TARGET_LDFLAGS) \
		`$(STAGING_DIR_HOST)/bin/pkg-config --libs qmi-glib qrtr-glib json-c`
endef

define Package/ckb01-modem/install
	$(INSTALL_DIR) $(1)/usr/sbin $(1)/lib/netifd/proto $(1)/etc/init.d $(1)/etc/rc.d $(1)/usr/share/ckb01-modem/heartbeat
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/ckb01-modem $(1)/usr/sbin/
	$(INSTALL_BIN) ./files/ckb01_qmi.sh $(1)/lib/netifd/proto/
	$(INSTALL_BIN) ./files/ckb01-update $(1)/lib/netifd/
	$(INSTALL_BIN) ./files/ckb01-session $(1)/usr/sbin/
	$(INSTALL_BIN) ./files/ckb01-n78-test $(1)/usr/sbin/
	$(INSTALL_BIN) ./files/ckb01-modem-init $(1)/etc/init.d/ckb01-modem
	$(INSTALL_BIN) ./files/ckb01-heartbeat-init $(1)/etc/init.d/ckb01-heartbeat
	$(INSTALL_DATA) ./files/heartbeat-index.html $(1)/usr/share/ckb01-modem/heartbeat/index.html
	$(LN) ../init.d/ckb01-heartbeat $(1)/etc/rc.d/S14ckb01-heartbeat
	$(INSTALL_BIN) ./files/ckb01-modem-wait $(1)/usr/sbin/
	$(INSTALL_BIN) ./files/ckb01-mhi-debug $(1)/usr/sbin/
	$(LN) ../init.d/ckb01-modem $(1)/etc/rc.d/S96ckb01-modem
	$(CP) ./files/endpoint-evidence.json $(1)/usr/share/ckb01-modem/
	$(CP) ./files/mbn-sha256.json $(1)/usr/share/ckb01-modem/
endef
$(eval $(call BuildPackage,ckb01-modem))
