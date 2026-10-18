# ~/.bashrc: executed by bash(1) for non-login shells.
# see /usr/share/doc/bash/examples/startup-files (in the package bash-doc)
# for examples

# If not running interactively, don't do anything
case $- in
    *i*) ;;
      *) return;;
esac


# ----------------------------------------------------------------------
export HISTCONTROL=ignoredups:erasedups  # no duplicate entries
export HISTSIZE=100000                   # big big history
export HISTFILESIZE=100000               # big big history
shopt -s histappend                      # append to history, don't overwrite it

# Save history after each command, but do not reload it immediately, to avoid mixing histories in terminals
export PROMPT_COMMAND="history -a"
# ----------------------------------------------------------------------
# From man builtins:
# -a     Append the ``new'' history lines to the history file.  These are history lines entered since the beginning of the current bash session, but not already appended to the history file.
# -c     Clear the history list by deleting all the entries.
# -r     Read the contents of the history file and append them to the current history list.

# -n     Read the history lines not already read from the history file into the current history list.  These are lines appended to the history file since the beginning of the current bash session.
# -w     Write the current history list to the history file, overwriting the history file's contents.

# check the window size after each command and, if necessary,
# update the values of LINES and COLUMNS.
shopt -s checkwinsize

# If set, the pattern "**" used in a pathname expansion context will
# match all files and zero or more directories and subdirectories.
#shopt -s globstar

# make less more friendly for non-text input files, see lesspipe(1)
[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# set variable identifying the chroot you work in (used in the prompt below)
if [ -z "${debian_chroot:-}" ] && [ -r /etc/debian_chroot ]; then
    debian_chroot=$(cat /etc/debian_chroot)
fi

# set a fancy prompt (non-color, unless we know we "want" color)
case "$TERM" in
    xterm-color|*-256color) color_prompt=yes;;
esac

# uncomment for a colored prompt, if the terminal has the capability; turned
# off by default to not distract the user: the focus in a terminal window
# should be on the output of commands, not on the prompt
force_color_prompt=yes

if [ -n "$force_color_prompt" ]; then
    if [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then
	# We have color support; assume it's compliant with Ecma-48
	# (ISO/IEC-6429). (Lack of such support is extremely rare, and such
	# a case would tend to support setf rather than setaf.)
	color_prompt=yes
    else
	color_prompt=
    fi
fi

if [ "$color_prompt" = yes ]; then

    git_branch() {
        # In functions replace \[ and \] with \001 and \002
        local __green="\001\033[0;32m\002"
        local __red="\001\033[0;31m\002"
        local __yellow="\001\033[0;33m\002"
        local __bold_red="\001\033[1;31m\002"
        local __ps_clear="\001\033[0m\002"

        branch_name="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"

        if [ -z "${branch_name}" ];
        then
            return
        fi

        # Untracked files
        if [ -z "$(git ls-files --others --exclude-standard)" ];
        then
            has_untracked=0
        else
            has_untracked=1
        fi

        # Modified files
        if [ -z "$(git ls-files -m)" ];
        then
            has_modified=0
        else
            has_modified=1
        fi

        # Staged files
        if [ -z "$(git diff --name-only --cached --diff-filter=AM)" ];
        then
            has_staged=0
        else
            has_staged=1
        fi

        if [ "$has_modified" = 1 ];
        then
            color=$__red
        elif [ "$has_staged" = 1 ];
        then
            color=$__red
        elif [ "$has_untracked" = 1 ];
        then
            color=$__yellow
        else
            color=$__green
        fi

        printf "${color}[$branch_name]$__ps_clear\n"
    }

    override_color_ps1 () {
        local __green="\[\033[01;32m\]"
        local __blue="\[\033[01;34m\]"
        local __byellow="\[\033[01;33m\]"
        local __azure="\[\033[01;36m\]"
        local __debian_chroot="${debian_chroot:+($debian_chroot)}"
        local __ps_clear="\[\033[0m\]"
        local __nnn_level=""
        [ ! -z $NNNLVL ] && __nnn_level="(nnn: $NNNLVL) "
        export PS1="$__debian_chroot$__green\u@\h$__ps_clear:$__blue\w \$(git_branch)$__ps_clear\$ "
    }

    override_color_ps1
    # PS1='${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
else
    PS1='${debian_chroot:+($debian_chroot)}\u@\h:\w\$ '
fi
unset color_prompt force_color_prompt

# If this is an xterm set the title to user@host:dir
case "$TERM" in
xterm*|rxvt*)
    PS1="\[\e]0;${debian_chroot:+($debian_chroot)}\u@\h: \w\a\]$PS1"
    ;;
*)
    ;;
esac

# enable color support of ls and also add handy aliases
if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias ls='ls --color=auto'
    #alias dir='dir --color=auto'
    #alias vdir='vdir --color=auto'

    alias grep='grep --color=auto'
    alias fgrep='fgrep --color=auto'
    alias egrep='egrep --color=auto'
fi

# colored GCC warnings and errors
#export GCC_COLORS='error=01;31:warning=01;35:note=01;36:caret=01;32:locus=01:quote=01'

# some more ls aliases
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'

# Add an "alert" alias for long running commands.  Use like so:
#   sleep 10; alert
alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'

# Alias definitions.
# You may want to put all your additions into a separate file like
# ~/.bash_aliases, instead of adding them here directly.
# See /usr/share/doc/bash-doc/examples in the bash-doc package.

if [ -f ~/.bash_aliases ]; then
    . ~/.bash_aliases
fi

# enable programmable completion features (you don't need to enable
# this, if it's already enabled in /etc/bash.bashrc and /etc/profile
# sources /etc/bash.bashrc).
if ! shopt -oq posix; then
  if [ -f /usr/share/bash-completion/bash_completion ]; then
    . /usr/share/bash-completion/bash_completion
  elif [ -f /etc/bash_completion ]; then
    . /etc/bash_completion
  fi
fi

# first, source the user env file
source /tmp/.env 2> /dev/null

# create aliases for ffprobe and ffmpeg to disable the default banner
alias ffprobe='ffprobe -hide_banner'
alias ffmpeg='ffmpeg -hide_banner'

# disable core dump by limiting the max size of a core dump to 0 bytes
ulimit -c 0

export PATH="/opt/uv/bin/:$PATH"

SPX_COMPLETIONS_PATH="/home/${USER}/.bash_completions/spx.sh"

# # Wait until the file exists
# while [[ ! -e "$SPX_COMPLETIONS_PATH" ]]; do
#   id
#   ls -l ~/.bash_completions/
#   ls -l "${SPX_COMPLETIONS_PATH}"
#   sleep 1
# done

# Source custom per-user bashrc modification
source "/home/${USER}/.bashrc_custom_${USER}.bash"

# add autocompletion for smallpixels.deploykit
source "${SPX_COMPLETIONS_PATH}"

export USER=`id -un`
export GROUP=`id -gn`
