import re
import os
import glob
import sys
import pdfplumber
from pprint import pprint
from collections import OrderedDict
from PyPDF2 import PdfFileReader


def getfiles(folder, extension):
    # Get the list of PDF files
    files = []
    filepath = folder + "/**/" + extension
    for file in glob.iglob(filepath, recursive=True):
        files.append(file)
    return files


def readini(fname):
    #  Read .ini file
    with open(fname) as file:
        result = file.readlines()
    return result


def getformfields(obj, tree=None, retval=None, fileobj=None):
    # Got this function from the resource:
    # https://exceptionshub.com/how-to-extract-pdf-fields-from-a-filled
    # -out-form-in-python.html

    """
    Extracts field data if this PDF contains interactive form fields.
    The *tree* and *retval* parameters are for recursive use.

    :param fileobj: A file object (usually a text file) to write
        a report to on all interactive form fields found.
    :return: A dictionary where each key is a field name, and each
        value is a :class:`Field<PyPDF2.generic.Field>` object. By
        default, the mapping name is used for keys.
    :rtype: dict, or ``None`` if form data could not be located.
    """
    fieldAttributes = {'/FT': 'Field Type', '/Parent': 'Parent',
    '/T': 'Field Name', '/TU': 'Alternate Field Name', '/TM': 'Mapping Name',
    '/Ff': 'Field Flags', '/V': 'Value', '/DV': 'Default Value'}
    if retval is None:
        retval = OrderedDict()
        catalog = obj.trailer["/Root"]
        # get the AcroForm tree
        if "/AcroForm" in catalog:
            tree = catalog["/AcroForm"]
        else:
            return None
    if tree is None:
        return retval
    obj._checkKids(tree, retval, fileobj)
    for attr in fieldAttributes:
        if attr in tree:
            # Tree is a field
            obj._buildField(tree, retval, fileobj, fieldAttributes)
            break
    if "/Fields" in tree:
        fields = tree["/Fields"]
        for f in fields:
            field = f.getObject()
            obj._buildField(field, retval, fileobj, fieldAttributes)
    return retval


def getfields(fn):
    # Read form  fields
    pdf = PdfFileReader(open(fn, 'rb'))
    fields = getformfields(pdf)
    return OrderedDict((k, v.get('/V', '')) for k, v in fields.items())


def gettextfields(i1, i2, fn):
    # Get text fields
    # fn is the name of the file to analyze...
    # i1 and i2 are the names of the .ini files...
    dic = OrderedDict()
    # Find the correct .ini file to use by finding a text in the pdf
    # that is specific for that file.
    with pdfplumber.open(fn) as pdf:
        text_in_pdf = pdf.pages[0].extract_text()
    if "Cod. Client" in text_in_pdf:
        inifile = i1
    elif "Cliente / Customer" in text_in_pdf:
        inifile = i2
    else:
        inifile = []
    # Extract pdf into a table
    table = pdf.pages[0].extract_table()

    # Read .ini file and put textfields from table into a dictionary
    for line in inifile:
        if "|" not in line:
            textfield = line.strip('\n').split("=")
            if len(textfield) == 1:
                textfield.append(textfield[0])
            # textfield[1] is the word in the pdf
            # textfield[0] is the word that shall be used in the dictionary
            for row in table:
                for i, col in enumerate(row):
                    if (col is not None) and (col.startswith(textfield[1])):
                        # This works as long as the value is on the row below
                        # with the same column as the searched textfield
                        dic[textfield[0]] = table[table.index(row)+1][i]
    # Return the .ini-file that shall be used and
    # a dictionary with the textfields
    return dic


def selectlist(all_lines, k, v):
    all_lines.append("""function selectedIdx(s, v) {
    for (var i = 0; i < s.options.length; i++) {
        if (s.options[i].text == v) {s.options[i].selected = true; return;}
    }
}\n""")
    return all_lines


def createscript(i1, i2, fields, txtfields, fn):
    all_lines = []
    # Extract file name without file extension
    filename = os.path.splitext(os.path.basename(fn))[0]
    # Add file extension '.txt'
    filename = filename + ".txt"

    # Find the correct .ini file to use by finding a text in the pdf
    # that is specific for that file.
    with pdfplumber.open(fn) as pdf:
        text_in_pdf = pdf.pages[0].extract_text()
    if "Cod. Client" in text_in_pdf:
        inifile = i1
    elif "Cliente / Customer" in text_in_pdf:
        inifile = i2
    else:
        inifile = []
    selectedIdx_exist = False
    for line in inifile:
        if "|" in line:
            formfield = line.strip('\n').split("|")
            if formfield[1] == 'e':
                field = formfield[0]
                value = fields[field]
                all_lines.append(
                "document.getElementById('"+field+"').value ='"+value+"'\n")
            elif formfield[1] == 's':
                field = formfield[0]
                value = fields[field]
                if not selectedIdx_exist:
                    all_lines = selectlist(all_lines, field, value)
                    selectedIdx_exist = True
                all_lines.append("selectedIdx(document.getElementById('"
                +field+"'), '"+value+"')\n")
    # Save text file
    #with open(filename, "a") as file:
    for text in txtfields:
        if txtfields[text]:
            all_lines.append("document.getElementById('"+text+"').value = '"
            +txtfields[text]+"'\n")

    with open(filename, "w") as file:
        #for line in all_lines:
        file.writelines(all_lines)
    return None


def execute():
    folder = "/your folder/formats/"
    extension = "*.pdf"

    try:
        i1 = readini('i1.ini') # Read the 1st .ini file
        i2 = readini('i2.ini') # Read the 2nd .ini file

        files = getfiles(folder, extension) # Find PDF files.

        for file in files:
            # Get textfields that are specified in the .ini file,
            # the inifile contains the .ini file that was used.
            textfields = gettextfields(i1, i2, file)

            # Find form fields and its values.
            formfields = getfields(file)

            # Create script
            createscript(i1, i2, formfields, textfields, file)

    except BaseException as msg:
        print('Error occured: ' + str(msg))

if __name__ == '__main__':
    execute()
