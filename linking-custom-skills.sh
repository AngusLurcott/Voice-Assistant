#!/usr/bin/env bash

# Run this script after the dev-setup has been completed

SKILLS_DIR="/opt/mycroft/skills"

CUSTOM_SKILL_DIR="custom_skills"

TOP=$(pwd -L)

function install_requirements_from_subdirs() {
    echo "Installing Requirements for Custom Skills"
    for skill_dir in "$TOP/$CUSTOM_SKILL_DIR"/*/; 
    do
        echo "Currently in $skill_dir"
        if [ -f "$skill_dir/requirements.txt" ]; then
            mycroft-pip install -r "$skill_dir/requirements.txt"
        fi
    done
}

for var in "$@" ; do
    # Check for options
    if [[ $var == '-ir' || $var == '--install-requirements' ]] ; then
        if install_requirements_from_subdirs; then
            exit 0
        else
            exit 1
        fi
    fi
done

if [ -d "$SKILLS_DIR" -a -d "$CUSTOM_SKILL_DIR" ]; then
    echo "Removing any broken soft links..."
    find "$SKILLS_DIR" -xtype l -exec rm '{}' \;

    echo "Updating Soft Links From Custom Skill directory..."
    find "$TOP/$CUSTOM_SKILL_DIR/" -maxdepth 1 -mindepth 1 -type d -exec ln -s '{}' "$SKILLS_DIR/" \;

else
    echo "Something went wrong, either the that both directories exist"
fi