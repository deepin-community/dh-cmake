%:
	dh $@ --buildsystem=cmake --with cpack

override_dh_auto_test:
