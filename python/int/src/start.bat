#!/bin/bash
clear

SOL_DIR="/home/weneck/school/IPP_latest/ipp26-project-templates-main/tests_homemade"
XML_DIR="/home/weneck/school/IPP_latest/ipp26-project-templates-main/tests_homemade_xml"
SOL2XML="/home/weneck/school/IPP_latest/ipp26-project-templates-main/sol2xml/sol_to_xml.py"

for sol_file in "$SOL_DIR"/*.sol26; do
    # Get just the filename without path and extension
    base=$(basename "$sol_file" .sol26)
    xml_file="$XML_DIR/$base.xml"

    echo "Processing: $base.sol26"
    python "$SOL2XML" "$sol_file" > "$xml_file"
    python -m solint -s "$xml_file"
    echo "---"
done