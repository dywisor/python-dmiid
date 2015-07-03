unexport PYTHONDONTWRITEBYTECODE
export PYTHONDONTWRITEBYTECODE=y

SHELL                 ?= sh

_PRJNAME              := dmiid
_PN                   := $(_PRJNAME)

S                     := $(CURDIR)
O                     := $(S)
BUILDDIR              := $(O)/tmp
VERSION_FILE          := $(S)/VERSION
PKG_DISTDIR           := $(O)/release
SRC_DOCDIR            := $(S)/doc
_EPYDOC_DIR           := $(SRC_DOCDIR)/epydoc
_BUILDSCRIPTS_DIR     := $(S)/build-scripts


DISTNAME               = $(_PRJNAME)
RELEASE_NOT_DIRTY      = n
RELEASE_DIRTY_SUFFIX   = -dirty
VBUMP_COMMIT           = y
DIST_PYDOC             = y
DIST_TAR               = n
DIST_GZIP              = n
DIST_BZIP2             = n
DIST_XZ                = y

PYVER                  =
PYTHON                 = python$(PYVER)

SETUP_PY               = $(S)/setup.py
_SETUP_PY_DIRS        := $(addprefix $(S)/,build/ $(_PRJNAME).egg-info/)
_PYMOD_DIRS           := $(addprefix $(S)/,$(_PRJNAME)/)

BX_SETVER             := $(_BUILDSCRIPTS_DIR)/setver.sh

MKDIR                  = mkdir
MKDIRP                 = $(MKDIR) -p
RM                     = rm
RMF                    = $(RM) -f
MV                     = mv
MVF                    = $(MV) -f
X_GIT                  = git
X_GZIP                 = gzip
X_BZIP2                = bzip2
X_XZ                   = xz
X_EPYDOC               = epydoc

_TRUE_WORDS           := y Y 1 yes YES true TRUE


PHONY += all
all:


PHONY += clean
clean:
	$(RMF) -r -- \
		$(_SETUP_PY_DIRS) \
		$(BUILDDIR)/ \
		$(wildcard $(PKG_DISTDIR)/*.make_tmp)

PHONY += epydoc-clean
epydoc-clean:
	$(RMF) -r -- $(_EPYDOC_DIR)

PHONY += pyclean
pyclean:
	find $(_PYMOD_DIRS) -name '*.py[co]' -delete -print

PHONY += distclean
distclean: clean pyclean epydoc-clean

PHONY += epydoc
epydoc: $(_EPYDOC_DIR)

$(_EPYDOC_DIR): epydoc-clean FORCE
	$(MKDIRP) $(@D)
	$(X_EPYDOC) --html -v -o $(@) $(_PYMOD_DIRS)


$(PKG_DISTDIR):
	$(MKDIRP) $(@)

# creates a src tarball (.tar)
PHONY += _dist
_dist: epydoc | $(PKG_DISTDIR)
	$(eval OUR_DIST_BASEVER  := $(shell cat $(VERSION_FILE)))
	test -n '$(OUR_DIST_BASEVER)'

	$(eval OUR_DIST_HEADREF := $(shell $(X_GIT) rev-parse --verify HEAD))
	test -n '$(OUR_DIST_HEADREF)'

	$(eval OUR_DIST_VREF    := $(shell $(X_GIT) rev-parse --verify $(OUR_DIST_BASEVER) 2>/dev/null))

ifeq ($(RELEASE_NOT_DIRTY),$(filter $(RELEASE_NOT_DIRTY),$(_TRUE_WORDS)))
	$(eval OUR_DIST_VER     := $(OUR_DIST_BASEVER))
else
	$(eval OUR_DIST_VER     := $(OUR_DIST_BASEVER)$(shell \
		test "$(OUR_DIST_HEADREF)" = "$(OUR_DIST_VREF)" || printf '%s' '$(RELEASE_DIRTY_SUFFIX)'))
endif

	$(eval OUR_DIST_FILE    := $(PKG_DISTDIR)/$(DISTNAME)_$(OUR_DIST_VER).tar)
	$(eval OUR_DIST_DOCFILE := $(PKG_DISTDIR)/$(DISTNAME)-doc_$(OUR_DIST_VER).tar)

	$(X_GIT) archive --worktree-attributes --format=tar HEAD \
		--prefix=$(DISTNAME)_$(OUR_DIST_VER)/ > $(OUR_DIST_FILE).make_tmp

	tar c \
		--owner=root --group=root \
		--xform='s=^[.]\($$\|/\)=$(DISTNAME)_$(OUR_DIST_VER)/=' \
		-C $(SRC_DOCDIR)/ . -f $(OUR_DIST_DOCFILE).make_tmp


PHONY += _dist_compress
_dist_compress::

ifeq ($(DIST_BZIP2),$(filter $(DIST_BZIP2),$(_TRUE_WORDS)))
_dist_compress:: _dist
	$(X_BZIP2) -c $(OUR_DIST_FILE).make_tmp    > $(OUR_DIST_FILE).bz2
	$(X_BZIP2) -c $(OUR_DIST_DOCFILE).make_tmp > $(OUR_DIST_DOCFILE).bz2
endif

ifeq ($(DIST_GZIP),$(filter $(DIST_GZIP),$(_TRUE_WORDS)))
_dist_compress:: _dist
	$(X_GZIP)  -c $(OUR_DIST_FILE).make_tmp    > $(OUR_DIST_FILE).gz
	$(X_GZIP)  -c $(OUR_DIST_DOCFILE).make_tmp > $(OUR_DIST_DOCFILE).gz
endif

ifeq ($(DIST_XZ),$(filter $(DIST_XZ),$(_TRUE_WORDS)))
_dist_compress:: _dist
	$(X_XZ)    -c $(OUR_DIST_FILE).make_tmp    > $(OUR_DIST_FILE).xz
	$(X_XZ)    -c $(OUR_DIST_DOCFILE).make_tmp > $(OUR_DIST_DOCFILE).xz
endif


PHONY += dist
dist: _dist _dist_compress
ifeq ($(DIST_TAR),$(filter $(DIST_TAR),$(_TRUE_WORDS)))
	$(MVF) -- $(OUR_DIST_FILE).make_tmp    $(OUR_DIST_FILE)
	$(MVF) -- $(OUR_DIST_DOCFILE).make_tmp $(OUR_DIST_DOCFILE)
else
	$(RM) -- $(OUR_DIST_FILE).make_tmp
	$(RM) -- $(OUR_DIST_DOCFILE).make_tmp
endif


PHONY += version
version:
	@cat $(VERSION_FILE)

PHONY += setver
setver: $(BX_SETVER)
ifeq ($(VER),)
	$(error $$VER is not set)
else
	$< $(VER)
endif

PHONY += version-bump
version-bump: $(BX_SETVER)
	{ ! $(X_GIT) status --porcelain -- $(notdir $(VERSION_FILE)) | grep .; }
ifeq ($(VBUMP_COMMIT),$(filter $(VBUMP_COMMIT),$(_TRUE_WORDS)))
	X_GIT="$(X_GIT)" $< --reset --git-add --git-commit --git-tag +
else
	X_GIT="$(X_GIT)" $< --reset --git-add +
endif




FORCE:

.PHONY: $(PHONY)
