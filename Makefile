PHONY: install
install:
	bash ./scripts/setup_mac.sh
	bash ./scripts/install_apps.sh

PHONY: setup_mac
setup_mac:
	bash ./scripts/setup_mac.sh

PHONY: install_apps
install_apps:
	bash ./scripts/install_apps.sh
