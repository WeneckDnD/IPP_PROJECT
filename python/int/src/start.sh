
clear

SOL_DIR="/Users/marek/Tedy/code/IPP_PROJECT/tests_homemade"
XML_DIR="/Users/marek/Tedy/code/IPP_PROJECT/tests_homemade_xml"
SOL2XML="/Users/marek/Tedy/code/IPP_PROJECT/sol2xml/sol_to_xml.py"

for sol_file in "$SOL_DIR"/*.sol26; do
    base=$(basename "$sol_file" .sol26)
    xml_file="$XML_DIR/$base.xml"

    echo "Processing: $base.sol26"
    python3 "$SOL2XML" "$sol_file" > "$xml_file"
    python3 -m solint -s "$xml_file"
    echo "---"
done