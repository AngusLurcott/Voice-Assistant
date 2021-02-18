#!/usr/bin/env bash

# Run this script after the dev-setup has been completed

SKILLS_DIR="/opt/mycroft/skills"

CUSTOM_SKILL_DIR="custom_skills"

TOP=$(pwd -L)

if [ -d "$SKILLS_DIR" -a -d "$CUSTOM_SKILL_DIR" ]; then
    echo "Installing Requirements for Custom Skills"

    echo "Removing any broken soft links..."
    find "$SKILLS_DIR" -xtype l -exec rm '{}' \;

    echo "Updating Soft Links From Custom Skill directory..."
    find "$TOP/$CUSTOM_SKILL_DIR/" -maxdepth 1 -mindepth 1 -type d -exec ln -s '{}' "$SKILLS_DIR/" \;

else
    echo "Something went wrong, either the that both directories exist"
fi