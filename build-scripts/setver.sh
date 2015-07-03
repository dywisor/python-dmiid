#!/bin/sh
#
#  Sets the version.
#
print_help() {
cat << EOF | sed -re 's,^[#]\s?,,'
#  Usage: setver [-S,--src <dir>] [--pretend] [--suffix <str>] [--reset]
#            [--git-add] [--git-commit] [--force-commit] [--git-tag]
#            [+,pbump|++,mbump|Mbump|[setver] <ver>]
#
# Actions:
#  +, pbump        -- increase patchlevel by one
#  ++, mbump       -- increase minor version by one and set patchlevel to 0
#  Mbump           -- increase major version by one and set minor/patchlevel to 0
#  setver <ver>    -- set a specific version
#
# Options:
# -S, --src <dir>  -- set project's source directory (default: $PWD)
# --pretend        -- just show what would be done
# --suffix <str>   -- replace old version suffix with <str>
# -l, --list-files -- just list files that would be edited by this script
#                      (usage example: setver -l | xargs git checkout HEAD --)
# --reset          -- check out VERSION file from git HEAD before doing anything
# --git-add        -- git-add modified files
# --git-commit     -- commit changes (commit message: "python-dmiid <newver>")
# --force-commit   -- enforce git commit (allow other files)
# --git-tag        -- run git-tag <newver> after git-commit
#
EOF
}
set -e
set -u
readonly IFS_DEFAULT="${IFS}"

readonly PY_FILES_TO_EDIT="dmiid/__init__.py setup.py"
readonly X_GIT="${X_GIT:-git}"
readonly COMMIT_MSG_HEADER="python-dmiid"

# get_git_commit_message ( new_version, **commit_msg! )
#
#  Creates a commit message and stores it in $commit_msg.
#  An empty str can be set if no commit should be made.
#
get_git_commit_message() {
   commit_msg="${COMMIT_MSG_HEADER:?} ${1:?}"
}

# get_git_tag ( new_version, **tag! )
#
#  Creates a git tag str and stores it in $tag.
#  An empty str suppresses tag creation.
#
get_git_tag() {
   tag="${1:?}"
}

# @noreturn die ( [message], [exit_code] ), raises exit($exit_code)
#
#  Lets the script die.
#
die() {
   echo "${1:+died: }${1:-died.}" 1>&2; exit ${2:-2};
}

# autodie ( *cmdv )
#
#  Runs *cmdv and dies on non-zero return.
#  ("set -ex" is too verbose)
#
autodie() {
   "$@" || die "command '${*}' returned ${?}." ${?}
}

# parse_version ( version_str, **major!, **minor!, **plvl!, **suffix! )
#
#  Splits a version_str into its components.
#
#  Example: 0.2.6-pre1 => major=0 minor=2 plvl=6 suffix=-pre1
#
parse_version() {
   unset -v major minor plvl suffix
   local IFS="."
   set -- ${1}
   IFS="${IFS_DEFAULT}"
   [ -n "${1-}" ] && [ -n "${2-}" ] && [ -n "${3-}" ] || return 2

   major="${1:?}"
   minor="${2:?}"
   plvl="${3:?}"
   shift 3 || die "error in parse_version()"
   suffix=
   while [ ${#} -gt 0 ]; do suffix="${suffix}.${1}"; shift; done
   suffix="${suffix#.}"
}

# inc ( k, **v0! )
#
#  Increments $k by one and stores the result in $v0.
#
inc() {
   v0=$(( ${1:?} + 1 ))
   # unlikely:
   [ ${v0} -gt ${1} ] || die "overflow"
}

# do_git_add ( *files, **want_gitadd, **X_GIT )
#
do_git_add() {
   ${want_gitadd} || return 0
   printf "git-add: %s\n" "${*}"
   ${want_pretend} || autodie "${X_GIT}" add -- "$@"
}

# do_git_commit_and_tag (
#    version_str, numfiles_changed,
#    **want_gitcommit, **want_forcecommit, **want_gittag, **X_GIT
# )
#
do_git_commit_and_tag() {
   ${want_gitcommit} || return 0
   local commit_msg commit_type tag

   autodie get_git_commit_message "${1}"
   autodie get_git_tag "${1}"

   if [ -z "${commit_msg}" ]; then
      return 0
   elif ${want_pretend}; then
      commit_type=maybe
   elif \
      [ $(git status --porcelain -- . | grep -c -- ^[MADRCU]) -eq ${2} ]
   then
      commit_type=clean
   elif ${want_forcecommit}; then
      commit_type=forced
   else
      die "cannot commit changes (try --force-commit)."
   fi

   printf "git-commit [%s]: %s\n" "${commit_type}" "${commit_msg}"
   ${want_pretend} || autodie "${X_GIT}" commit -m "${commit_msg}"

   ${want_gittag} && [ -n "${tag}" ] || return 0
   printf "git-tag: %s\n" "${tag}"
   ${want_pretend} || autodie "${X_GIT}" tag "${tag}"
}


# set defaults / parse args
autodie hash "${X_GIT}"
S="${PWD}"
unset -v V
unset -v ACTION
unset -v new_suffix

readonly _boolvars="pretend gitadd gitcommit forcecommit gittag reset"
for iter in ${_boolvars}; do eval "want_${iter}=false"; done

doshift=
while [ ${#} -gt 0 ]; do
   doshift=1
   case "${1}" in
      '') : ;;

      -S|--src)
         [ -n "${2-}" ] || die "one non-empty arg required after '${1}'."
         doshift=2
         S="${2:?}"
      ;;

      --pretend)      want_pretend=true     ;;
      --reset)        want_reset=true       ;;
      --git-add)      want_gitadd=true      ;;
      --git-commit)   want_gitcommit=true   ;;
      --force-commit) want_forcecommit=true ;;
      --git-tag)      want_gittag=true      ;;

      [Mmp]bump)      ACTION="${1}" ;;
      '+')            ACTION=pbump  ;;
      '++')           ACTION=mbump  ;;
      *.*.*)          ACTION=setver; V="${1}" ;;
      *.*.*[-_]*)     ACTION=setver; V="${1}"; new_suffix= ;;

      setver)
         [ -n "${2-}" ] || die "one non-empty arg required after '${1}'."
         doshift=2
         ACTION=setver
         V="${2:?}"
      ;;

      --suffix)
         [ -n "${2+SET}" ] || die "one arg required after '${1}'."
         doshift=2
         new_suffix="${2?}"
      ;;

      -l|--list-files)
         for fname in ${PY_FILES_TO_EDIT}; do echo "${fname}"; done
         echo "VERSION"
         exit 0
      ;;
      -h|--help)
         print_help
         exit 0
      ;;

      *)
         die "unknown arg: ${1}" 64
      ;;
   esac
   [ ${doshift} -eq 0 ] || shift ${doshift} || die "argparse: shift failed"
done

! { ${want_gittag} || ${want_forcecommit}; } || want_gitcommit=true
! ${want_gitcommit} || want_gitadd=true

readonly S ACTION
for iter in ${_boolvars}; do readonly "want_${iter}"; done

cd "${S}" || die "chdir ${S}"

! ${want_reset} || autodie "${X_GIT}" checkout HEAD -- VERSION
readonly OLDVER="$(cat "${S}/VERSION")" || die "failed to read ${S}/VERSION"
autodie parse_version "${OLDVER}"
: ${new_suffix="${suffix}"}

# get new version
case "${ACTION-}" in
   pbump)
      inc "${plvl}"
      V="${major}.${minor}.${v0}"
   ;;
   mbump)
      inc "${minor}"
      V="${major}.${v0}.0"
   ;;
   Mbump)
      inc "${major}"
      V="${v0}.0.0"
   ;;
   setver)
      V="${V}${new_suffix}"
   ;;
   *)
      ${want_reset} || die "unknown or no action specified."
      exit 0
   ;;
esac


# edit files
q="\"\'"
re_pyfile_ver="^(\s*[_]*version[_]*\s*=\s*)[${q}]([^\s;,${q}]*)[${q}](\s*[;,]?\s*)\$"

v0=0
_fmt="edit %-18s: %8s  ->  %s\n"
for fname in ${PY_FILES_TO_EDIT}; do
   inc "${v0}"
   f="${S}/${fname}"
   fver="$(sed -rn -e "s@${re_pyfile_ver}@\2@p" < "${f}")"
   printf "${_fmt}" "${fname}" "${fver}" "${V}"
   ${want_pretend} || \
      autodie sed -r -e "s@${re_pyfile_ver}@\1\"${V}\"\3@" -i "${f}"
   do_git_add "${f}"
done

inc "${v0}"
printf "${_fmt}" "VERSION" "${OLDVER}" "${V}"
${want_pretend} || echo "${V}" > "${S}/VERSION" || die "failed to write VERSION"
do_git_add "${S}/VERSION"

[ ${v0} -gt 0 ] || die "numfiles?"
printf "edited %d files in total.\n" "${v0}"

autodie do_git_commit_and_tag "${V}" "${v0}"
