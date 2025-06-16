# --------------------------------*- sh -*-----------------------------------
# File: /openfoam/assets/welcome.sh
#
# Copyright (C) 2020-2023 OpenCFD Ltd.
# SPDX-License-Identifier: (GPL-3.0-or-later)
#
# General information to display on startup (interactive shell)
#
# ------------------------------------------------------------------------
unset optBrief

# Parse options
while [ "$#" -gt 0 ]
do
    case "$1" in
    (-brief)
        optBrief=true
        ;;
    esac
    shift
done


# Operating system name (may not be apparent for the user)
unset PRETTY_NAME
eval "$(sed -ne '/^PRETTY_NAME=/p' /etc/os-release 2>/dev/null)"

# Admin user
sudo_user=sudofoam
if [ -f /etc/sudoers.d/openfoam ]
then
    grep -q "^${sudo_user}:" /etc/passwd 2>/dev/null || unset sudo_user
else
    unset sudo_user
fi


# Find the (latest) installed version
unset prefix projectDir
findLatestOpenFOAM()
{
    prefix="$1"
    projectDir="$(/bin/ls -d "$prefix"/openfoam[0-9]* 2>/dev/null | sort -n | tail -1)"
}

if [ -f "/openfoam/META-INFO/api-info" ]
then
    # Installed directly under /openfoam
    unset prefix
    projectDir=/openfoam
else
    findLatestOpenFOAM /openfoam

    # Installed in system locations
    [ -n "$projectDir" ] || findLatestOpenFOAM /usr/lib/openfoam
fi


unset foam_api foam_patch foam_build release_notes

if [ -d "$projectDir" ]
then
    # META-INFO: api/patch/build values

    info="$projectDir/META-INFO/api-info"
    eval "$(sed -ne 's/^\(api\|patch\)=/foam_\1=/p' "$info" 2>/dev/null)"

    info="$projectDir/META-INFO/build-info"
    eval "$(sed -ne 's/^\(build\)=/foam_\1=/p' "$info" 2>/dev/null)"

    # Release notes: openfoam-vYYMM
    if [ -n "$foam_api" ]
    then
        release_notes="openfoam-v${foam_api}"
    fi
else
    unset projectDir
fi

# Build information - stringify like OpenFOAM output
unset build_string
if [ -n "$foam_api" ]
then
    build_string="${foam_build}${foam_build:+ }OPENFOAM=${foam_api}${foam_patch:+ patch=${foam_patch}}"
fi

# ---------------------------------------------------------------------------
# Output

exec 1>&2

if [ "$optBrief" = true ]
then
    cat<< __BRIEF__
---------------------------------------------------------------------------
System   :  ${PRETTY_NAME:-[]}${sudo_user:+  (admin user: $sudo_user)}
OpenFOAM :  ${projectDir:-[]}
Build    :  ${build_string:-[]}
Website  :  www.openfoam.com
---------------------------------------------------------------------------
__BRIEF__
    exit 0
fi

# Include location of container recipes to make it easier to make
# modified versions
cat<< '__BANNER__'
---------------------------------------------------------------------------
  =========                 |
  \\      /  F ield         | OpenFOAM in a container [from OpenCFD Ltd.]
   \\    /   O peration     |
    \\  /    A nd           | www.openfoam.com
     \\/     M anipulation  |
---------------------------------------------------------------------------
 Container Recipes:  https://develop.openfoam.com/packaging/containers
---------------------------------------------------------------------------
__BANNER__

cat<< __NOTES__
 Release notes:  https://www.openfoam.com/news/main-news/${release_notes}
 Documentation:  https://www.openfoam.com/documentation/
 Issue Tracker:  https://develop.openfoam.com/Development/openfoam/issues/
 Local Help:     more /openfoam/README
---------------------------------------------------------------------------
System   :  ${PRETTY_NAME:-[]}${sudo_user:+  (admin user: $sudo_user)}
OpenFOAM :  ${projectDir:-[]}
Build    :  ${build_string:-[]}
__NOTES__

if [ -n "$build_string" ]
then
    cat<< '__NOTES__'

Note
    Different OpenFOAM components and modules may be present (or missing)
    on any particular container installation.
    Eg, source code, tutorials, in-situ visualization, paraview plugins,
        external linear-solver interfaces etc.
__NOTES__
fi

cat<< '__FOOTER__'
---------------------------------------------------------------------------
__FOOTER__

# ---------------------------------------------------------------------------
