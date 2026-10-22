# Pinned DWC baseline

Linux 6.18.55 with OpenWrt a0d3cabc052f9c3c19a0abe2b2633195f703bccc
(JuliusBairaktaris/openwrt-ppe-nss) generic backport-6.18 patches 907,
908-1, 908-2, 908-3 and 909 applied in that order, with fuzz=0.
These are the only patches in the pinned generic/qualcommax tree touching
these DWC source files. The fixture deliberately retains IRQ-work affinity
redirection, so diagnostic hooks cannot revert it to the vanilla dispatcher.

SHA256:

- `340c18b0bf677dc181911b54ba568c3dbd9a6a118d76644dbc0415476a2c8dd3` `drivers/pci/controller/dwc/pcie-designware-host.c`
- `556c8fca5e2b5f5b20b4d57bfdcefb4e967a6a6982c665bf88e862668ba7737d` `drivers/pci/controller/dwc/pcie-designware.h`
