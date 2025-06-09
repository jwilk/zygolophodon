# Copyright © 2024-2025 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

PYTHON = python3

PREFIX = /usr/local
DESTDIR =

bindir = $(PREFIX)/bin
basedir = $(PREFIX)/share/zygolophodon
mandir = $(PREFIX)/share/man

.PHONY: all
all: doc/zygolophodon.1

%.1: %.1.in README private/gen-manpage
	private/gen-manpage < $(<) > $(@).tmp
	mv $(@).tmp $(@)

.PHONY: install
install: zygolophodon all
	$(PYTHON) - < lib/__init__.py  # Python version check
	# executable:
	install -d $(DESTDIR)$(bindir)
	python_exe=$$($(PYTHON) -c 'import sys; print(sys.executable)') && \
	sed \
		-e "1 s@^#!.*@#!$$python_exe@" \
		-e "s#^basedir = .*#basedir = '$(basedir)/'#" \
		$(<) > $(<).tmp
	install $(<).tmp $(DESTDIR)$(bindir)/$(<)
	rm $(<).tmp
	# library:
	install -d $(DESTDIR)$(basedir)/lib
	install -p -m644 lib/*.py $(DESTDIR)$(basedir)/lib/
ifeq "$(DESTDIR)" ""
	umask 022 && $(PYTHON) -m compileall -q $(basedir)/lib/
endif
	# manual page:
	install -d $(DESTDIR)$(mandir)/man1
	install -p -m644 doc/$(<).1 $(DESTDIR)$(mandir)/man1/

.PHONY: test
test: verbose=
test: zygolophodon all
	prove $(and $(verbose),-v)

.PHONY: test-installed
test-installed: verbose=
test-installed: $(or $(shell command -v zygolophodon;),$(bindir)/zygolophodon)
	prove $(and $(verbose),-v) :: --installed

.PHONY: clean
clean:
	rm -f *.tmp doc/*.1 doc/*.tmp

.error = GNU make is required

# vim:ts=4 sts=4 sw=4 noet
