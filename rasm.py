#!/usr/bin/python3

# -*- python -*-

import sys
import re

'''
Author: Riki Borders
Due Date: 4/30/2021 10:00 PM
CS240 Final Project: Assembler Pass 1
'''

#NOTE: A word in SIC/XE = 3 bytes.
# That would mean a dword is 6 bytes.

#Global Dictionary of all format 1/2/3 instructions, and their sizes
instructions = {"ADD": 3,   "ADDF": 3,  "ADDR": 2,"AND": 3, "CLEAR": 2,"COMP": 3,
                "COMPF": 3, "COMPR": 2, "DIV": 3, "DIVF": 3,"DIVR": 2, "FIX": 1,
                "FLOAT": 1, "HIO": 1,   "J": 3,   "JEQ": 3, "JGT": 3,  "JLT": 3,
                "JSUB": 3,  "LDA": 3,   "LDB": 3, "LDCH": 3,"LDF": 3,  "LDL": 3,
                "LDS": 3,   "LDT": 3,   "LDX": 3, "LPS": 3, "MUL": 3,  "MULF": 3,
                "MULR": 2,  "NORM": 1,  "OR": 3,  "RD": 3,  "RMO": 2,  "RSUB": 3,
                "SHIFTL": 2,"SHIFTR": 2,"SIO": 1, "SSK": 3, "STA": 3,  "STB": 3,
                "STCH": 3,  "STF": 3,   "STI": 3, "STL": 3, "STS": 3,  "STSW": 3,
                "STT": 3,   "STX": 3,   "SUB": 3, "SUBF": 3,"SUBR": 2, "SVC": 2,
                "TD": 3,    "TIO": 1,   "TIX": 3, "TIXR": 2,"WD": 3}

extended_instructions = ["+add", "+addf", "+and", "+comp", "+compf","+div", "+divf",
                        "+j",   "+jeq", "+jgt",  "+jlt",  "+jsub",  "+lda", "+ldb",
                        "+ldch","+ldf", "+ldl",  "+lds",  "+ldt",   "+ldx", "+lps",
                        "+mul", "+mulf", "+or",  "+rd",   "+rsub",  "+ssk", "+sta",
                        "+stb", "+stch", "+stf", "+sti",  "+stl",   "+sts", "+stsw",
                        "+stt", "+stx",  "+sub",  "+subf","+td",    "+tix", "+wd"]

directives = ['BYTE', 'RESW', 'RESB', 'WORD']

# Global dictionary containing mnemonic's and their respective opcodes (in hex)
opcode_dict = { "ADD": '18',   "ADDF": '58',  "ADDR": '90',"AND": '40', "CLEAR": 'B4',"COMP": '28',
                "COMPF": '88', "COMPR": 'A0', "DIV": '24', "DIVF": '64',"DIVR": '9C', "FIX": 'C4',
                "FLOAT": 'C0', "HIO": 'F4',   "J": '3C',   "JEQ": '30', "JGT": '34',  "JLT": '38',
                "JSUB": '48',  "LDA": '00',   "LDB": '68', "LDCH": '50',"LDF": '70',  "LDL": '08',
                "LDS": '6C',   "LDT": '74',   "LDX": '04', "LPS": 'D0', "MUL": '20',  "MULF": '60',
                "MULR": '98',  "NORM": 'C8',  "OR": '44',  "RD": 'D8',  "RMO": 'AC',  "RSUB": '4C',
                "SHIFTL": 'A4',"SHIFTR": 'A8',"SIO": 'F0', "SSK": 'EC', "STA": '0C',  "STB": '78',
                "STCH": '54',  "STF": '80',   "STI": 'D4', "STL": '14', "STS": '7C',  "STSW": 'E8',
                "STT": '84',   "STX": '10',   "SUB": '1C', "SUBF": '5C',"SUBR": '94', "SVC": 'B0',
                "TD": 'E0',    "TIO": 'F8',   "TIX": '2C', "TIXR": 'B8',"WD": 'DC'}


# flag for base addressing, and the value in b register
''' WHEN YOU USE BASE_FLAG AND BASE_VAL MAKE SURE TO TYPE "global base_f/v"
    AT THE START OF THE FUNCTION'''
base_flag = False
base_val = None

# Dictionary to hold register values
reg_dict = {'A': '0', 'X': '1', 'L': '2', 'B': '3',
            'S': '4', 'T': '5', 'F': '6', 'PC': '8', 'SW': '9'}


def start():
    if (len(sys.argv) < 3):
        raise SystemExit("Usage: sasm <filename>")

    i_filename = sys.argv[1]
    o_filename = sys.argv[2]
    try:
        inFd = open(i_filename, "r")
    except IOError:
        raise SystemExit("Error opening input file: " + i_filename)

    # Generate labels and locations via pass1, for pass2
    label_dict, line_locations = pass1(inFd)

    # Re-open the file to start from the top, then run pass2
    # To generate object code
    inFd = open(i_filename, "r")
    pass2(inFd, o_filename, label_dict, line_locations)
    inFd.close()


def pass1(inFd):
    '''
    Perform Pass 1 of assembling process. This pass will parse all instructions
    PARAMS: inFd:file: file to read in
    RETURNS:
        label_dict:dictionary: dictionary containing labels and their locs
        line_locations:list: list of all line locations (in order from top of
                             the file to the bottom)
    '''
    # Initialize location, and dictionary for labels and their location
    location = '000000'
    label_dict = {}
    line_locations = []

    line = inFd.readline()

    # Process each line of the file & update location as we go
    while line != "":
        location, label_dict = parseInstruction(line, location, label_dict, line_locations)
        #line_locations.append(location)
        #print(location, line)
        line = inFd.readline()

    return label_dict, line_locations


def pass2(inFd, o_filename, label_dict, line_locations):
    '''
    Perform pass 2 of the assembling process. This pass will generate object
    code using the locations generated from the prvious pass (see pass1).
    Addressing mode priority is as follows: extended, base, pc-relative, direct,
    and finally SIC.
    PARAMS:
        inFd:file: file object to read in
        label_dict:dictionary: dictionary containing labels and their locations
        line_locations:list: list of line locations from top of file to bottom
    RETURNS: None
    '''
    global base_flag
    global base_val
    index = 0

    # Parallel lists with locations at the same indecies as obj code. This is
    # dont becuase some obj code/locations may be the same
    p2_locations = []
    p2_obj_code = []
    p2_mnemonics = []

    start_adr = '000000' # Save start address when we encounter it for the end record

    # Initialize a header record
    header_record = 'H      '
    # Calculate program length
    end = line_locations[len(line_locations) - 1]
    program_len_d = hex2dec(end) - hex2dec(start_adr)
    program_len = dec2hex(program_len_d) # Convert length to hex

    header_record += start_adr + program_len

    line = inFd.readline()
    # Process each line & generate object code accordingly
    while line != "":
        label = None
        location = line_locations[index]

        # Check for label line
        match = re.match(r"([A-Z_][A-Z_0-9]*):", line, re.IGNORECASE)
        if match:
            # Strip label
            line = line.lstrip() # Space check for good measure

            # Strip label based on colon pos
            pos = line.find(':')
            label = line[0:pos+1]

            # Grab the label and prepare line for further processing
            label = label.upper()
            line = line[pos+1:].lstrip() # Strip off label and leading whitespace

        # Fetch line's mnemonic and parameter.
        label, mnemonic, param = pass2_parseline(line, label)
        if mnemonic and mnemonic.upper() == 'TIXR':
            if ',' in param:
                raise SystemExit('Extraneous parameters')
        # Check for base directives
        if mnemonic and mnemonic.upper() in ['BASE', 'NOBASE']:
            obj_code = None
            base_flag = not base_flag # Set flag & check for value

            if base_flag:
                # Find target label and set b = address
                for label, address in label_dict.items():
                    if label.strip(':').upper() == param.upper():
                        base_val = address
                        break
                if base_val == None:
                    base_val = param

        else:
            # Get program counter
            if (index + 1) < len(line_locations):
                pc = line_locations[index + 1]

            # Generate object code for given line
            obj_code = generate_obj_code(label, mnemonic, param, location, label_dict, pc)
            p2_locations.append(location)
            p2_obj_code.append(obj_code)
            p2_mnemonics.append(mnemonic)

        # Check to create header record
        if mnemonic and mnemonic.upper() == 'START':
            header_record = 'H'
            # add 6 byte left justified title
            if label:
                title = label.strip(':')
                while len(title) != 6:
                    title = title + ' '
            else: # If no title, just put pad w/ spaces
                title = '      '
            # Make address 20 bits (3-byte binary encoding)
            start_address = param
            while len(start_address) != 6:
                start_address = '0' + start_address
                start_adr = start_address # Save for end record

            # Calculate program length
            end = line_locations[len(line_locations) - 1]
            program_len_d = hex2dec(end) - hex2dec(start_address)
            program_len = dec2hex(program_len_d) # Convert length to hex

            header_record += title + start_address + program_len

        elif mnemonic and mnemonic.upper() == 'END': # Create end record
            end_record = 'E'
            # Grab 20 bit entry point of program
            while len(start_adr) != 6:
                start_adr = '0' + start_adr
            end_record += start_adr

        # Update index & line
        index += 1
        line = inFd.readline()

    # Now that all object code have been generated, we want to generate
    # Text records. When we encounter any sort of byte reservation, end the record.
    text_records = []
    text_record = 'T' # initialize text record

    length = 0 # length of the text record (measured in bytes)
    accumulated = '' # used to track col. 10-69 when generating text record
    for i in range(len(p2_locations)):
        if not p2_obj_code[i]: # Check if line has no object code

            if not p2_mnemonics[i] and not p2_obj_code[i]: # if at a comment, keep it pushing.
                pass
            # If we encounter a reserve byte, end the text record
            elif p2_mnemonics[i] and 'RESW' in p2_mnemonics[i] or 'RESB' in p2_mnemonics[i]:
                    if text_record != 'T':
                        # Set record's length
                        s = dec2hex(length)[4:]
                        text_record = text_record + s + accumulated # construct record

                        text_records.append(text_record) # save record, reset variables
                        text_record = 'T'
                        length = 0
                        accumulated = ''
                    else:
                        pass

        else: # Add object code to appropriate text record
            obj_c = p2_obj_code[i]
            # Check if we must set the starting address
            if text_record == 'T':
                starting_address = p2_locations[i]
                while len(starting_address) != 6: # set to 6 bytes
                    starting_address = '0' + starting_address
                text_record += starting_address

            if length == 64: # Check if we exhausted our bytes
                # Set record's length
                s = dec2hex(length)[4:]
                text_record = text_record + s + accumulated # construct record

                text_records.append(text_record) # save record, reset variables
                text_record = 'T'
                length = 0
                accumulated = ''

                # Set the record's starting address
                starting_address = p2_locations[i]
                while len(starting_address) != 6: # set to 6 bytes
                    starting_address = '0' + starting_address
                text_record += starting_address

            code_size = len(obj_c) // 2 # divide by 2 to measure in bytes
            if length + code_size < 64: # Add bits if within 64 byte range
                accumulated += obj_c
                length += code_size

            elif length + code_size == 64: # Start a new record if at max length
                s = dec2hex(length)[4:]
                length += code_size # Process the object code
                accumulated += obj_c
                text_record = text_record + s + accumulated # construct record
                text_records.append(text_record)
                text_record = 'T' # Reset processing variables
                length = 0
                accumulated = ''
            else: # If record is greater than 64, just add the bits we can.
                bytes = []
                for i in range(0, len(obj_c), 2): # Split bits into bytes
                    if i != len(obj_c) - 1:
                        temp_byte = obj_c[i] + obj_c[i+1]
                        bytes.append(temp_byte)

                extra = []
                for byte in bytes: # Add the bits we can
                    if length + 1 <= 64:
                        accumulated += byte
                        length += 1
                    else:
                        extra.append(byte)

                # Set the record's starting address
                starting_address = dec2hex(hex2dec(starting_address) + length)
                while len(starting_address) != 6: # set to 6 bytes
                    starting_address = '0' + starting_address

                s = dec2hex(length)[4:]
                text_record = text_record + s + accumulated # construct record
                text_records.append(text_record)
                text_record = 'T' # Reset processing variables
                text_record += starting_address
                length = 0
                accumulated = ''

                for byte in extra: # Add the leftover bytes to the next record
                    accumulated += byte
                    length += 1

        # Check if we are at the end of the object code
        if i == len(p2_locations) - 1:
            # Set record's length
            s = dec2hex(length)[4:]
            text_record = text_record + s + accumulated # finalize whatever we have left
            text_records.append(text_record)

    # print(header_record)
    # for r in text_records:
    #     print(r)
    # print(end_record)

    write_bytes(o_filename, header_record, text_records, end_record)


def write_bytes(o_filename, header_record, text_records, end_record):
    '''
    Write the binary object records to a a file. Pieces of the function were
    provided by Prof. Bailey.
    PARAMS:
        o_filename:str: Name of the file we will write our bytes to
        header_record:str: header record generated by pass 2
        text_records:list: list of text records generated by pass 2
        end_record:str: end record generated by pass 2
    RETURNS: None
    '''
    fd = open(o_filename, "wb") #open/create output file (wb = write bytes)

    bytes = [] # List to hold generated bytes

    # Generate header record bytes
    bytes = [ord(char) for char in header_record[:7]]

    for i in range(0, len(header_record[7:]) - 1, 2): # iterate thru the header bytes
        bytes.append(hex2dec(header_record[7:][i:i+2])) # add together 2 nibbles to make our byte

    for rec in text_records: # Add the ascii value of  'T' (starts our text records)
        bytes += generate_record_bytes(rec)

    bytes += generate_record_bytes(end_record)

    fd.write(bytearray(bytes)) # Write our bytes then close file
    fd.close()


def generate_record_bytes(rec):
    '''
    Generate appropriate bytes from a record, so we can write them to a byte file
    PARAMS: rec:str: record we want to process (can be T, H, or E)
    RETURNS: bytes:list: list of our generated bytes
    '''
    bytes = []

    rec = rec.rstrip() # Strip off new line
    bytes.append(ord(rec[0]))
    for i in range(0, len(rec) - 1, 2): # iterate thru the record bytes
        bytes.append(hex2dec(rec[1:][i:i+2])) # add together 2 nibbles to make our byte

    return bytes


def generate_obj_code(label, mnemonic, param, location, label_dict, pc):
    '''
    This function will facilitate the generation of object code for the program.
    It will identify the mode needed to generate the object code, identify bits
    to be set, and handle the actual generation of object code. Even comment
    lines will have object code (i.e 000000).
    PARAMS:
        label:str: parsed line label
        mnemonic:str: parsed line mnemonic
        param:str: parsed line parameter
        location:str: location of the current line
        label_dict:dictionary: dictionary containing all pass1 labels:locations
        pc:str: program counter; location of the next line
    RETURNS:
        obj_code:str: generated object code for the given line.
    '''

    if param and param.upper() + ':' in label_dict.keys():
        param = label_dict[param.upper()+':'].strip()

    # If mnemonic is a NoneType, it's a comment. Return.
    if mnemonic == None:
        return None

    # Get opcode
    opcode = fetch_opcode(mnemonic)

    if opcode == '4C': 
        if param: # rsub shouldnt have a parameter
            raise SystemExit("Extraneous characters at end of line")
        bin_opcode = bin(hex2dec(opcode))[2:]
        while len(bin_opcode) < 8:
            bin_opcode = '0' + bin_opcode

        bin_l = list(bin_opcode) # listify and make it 8 bits
        bin_l[len(bin_l)-1] = '1'
        bin_l[len(bin_l)-2] = '1'

        new_binary = ''.join(bin_l)
        opcode = dec2hex(int(new_binary, 2))[4:]

        obj_code = generate_format1(opcode)
        while len(obj_code) < 6:
            obj_code = obj_code + '0'
        return obj_code

    if opcode and not param:
        obj_code = generate_format1(opcode)
        return obj_code

    elif param:
        m_param = param.upper()
        # If we have two registers, then use format 2
        reg_match = re.match("^([AXLBSTF]|SW|PC)( |\t|$|,)", m_param, re.IGNORECASE)
        if reg_match:
            obj_code = generate_format2(opcode, param, mnemonic)
            return obj_code

    # Check for word directive
    if mnemonic.upper() == 'WORD':
        obj_code = dec2hex(int(param))
        return obj_code

    # Identify correct format, and generate bits. If no opcode, skip

    # Extended has highest precedence, and is denoted by a '+'
    #extended, based, pc-relative, direct, and finally SIC

    if (mnemonic and param) and (mnemonic[0] == '+' or param[0] == '+'):
        obj_code = generate_format4(opcode, mnemonic, param, location, label_dict)
        return obj_code

    if opcode and instructions[mnemonic.upper()] > 2:
        obj_code = generate_format3(opcode, param, location, label_dict, pc)
        return obj_code

    else:   # Check for directives

        if mnemonic.upper() == 'BYTE': # Byte directive
            obj_code = obj_byte(param)
            return obj_code
        else:
            pass


def obj_byte(param):
    '''
    Convert byte directive into object code.
    PARAMS: param:str: byte parameter
    RETURNS: obj_code:str: generated object code
    '''
    if param[0].upper() == 'C':
        obj_list = []
        param = param[2:].strip("'") # Get characters
        p_list = list(param)

        for char in p_list: #Convert characters to hex vals & append
            char = dec2hex(ord(char)).lstrip('0')
            obj_list.append(char)

        obj_code = ''.join(obj_list)
    elif param[0].upper() == 'X':
        obj_code = param[2:].strip("'")


    return obj_code


def fetch_opcode(mnemonic):
    '''
    Match mnemonic to a listed instruction, and return the 2-hex-byte long
    opcode of the mnemonic.
    PARAMS:  mnemonic:str: mnemonic to fetch an opcode for
    RETURNS: opcode:str: located opcode for given instruction (1 bye/8 bits)
    '''
    # Check for unique bit-setters, so we can ignore them.
    bs = mnemonic[0]
    if bs == '+' or bs == '@' or bs == '#' or bs == 'x':
        mnemonic = mnemonic[1:]

    for ins, opc in opcode_dict.items():
        if mnemonic.upper() == ins.upper():
            return opc


def generate_format1(opcode):
    '''
    Generate object code for format 1. format 1  is just an 8 bit opcode. This
    function primarily serves as a way to document and order code. Note
    format1 doesnt reference memory at all
    PARAMS: opcode:str: opcode of the instruction's mnemonic
    RETURNS: opcode:str: 2 byte (16 bit) object code of the instruction.
    '''
    return opcode


def generate_format2(opcode, param, mnemonic):
    '''
    Generate object code for format 2. Note that format 2 does not reference
    memory at all, just like format 1. Format 2 contains an 8 bit opcode and
    2 registers. Format 2: 8 bit opcode|4 bit reg1|4 bit reg2.
    PARAMS:
        opcode:str: opcode of the instruction's mnemonic.
        param:str: program's parameter field (unparsed)
        mnemonic:str: line's mnemonic indicating operation to perform
    RETURNS: obj_code:str: opcode of the instruction's mnemonic
    '''
    obj_code = None

    # Check for two registers
    if ',' in param:
        s_pos = param.find(',')
        reg1 = param[:s_pos]
        reg2 = param[s_pos+1:].strip()

        for reg, val in reg_dict.items(): # Get register values
            if reg1.upper() == reg:
                reg1_val = val
            if reg2.upper() == reg:
                reg2_val = val

        # Generate object code
        obj_code = opcode + reg1_val + reg2_val

    else: # Single register case
        for reg, val in reg_dict.items(): # Locate target register/value in dict
            if param.upper() == reg:
                # Generate object code. I'm making the assumption that since
                # this is for 1-register instruction, we wont check 2nd half of
                # byte 2
                obj_code = opcode+val+'0'
                break

    return obj_code


def generate_format3(opcode, param, location, label_dict, pc):
    '''
    Generate the object code given an opcode, and its parameters. Since this is
    format 3, the total length will be 24 bits (3 bytes). Recall the format of
    format 3 is like so: opcode(6 bits)|N|I|X|B|P|E|disp (12 bits). Note the
    flags between the opcode and displacement are 1 bit each.
    PARAMS:
        opcode:str: opcode of the instruction's mnemonic
        param:str: Instruction's parameters (multiple items may be here, unparsed)
        location:str: location of the current line
        label_dict:dictionary: dictionary containing all pass1 labels:locations
        pc:str: program counter; location of the next line
    RETURNS:
        obj_code:str: 3 byte (24 bit) object code of the instruction.
    '''

    # Translate hex opcode into binary
    bin_opcode = bin(hex2dec(opcode))[2:]
    # If N and I bits arent used, they both must be set
    n_flag = True
    i_flag = True

    # Ensure we have 8 bits to work with
    while len(bin_opcode) != 8:
        bin_opcode = '0' + bin_opcode

    # Check for I and N bits being set. Note i and n bits affect opcode hexvalue
    i_match = re.match(r"[#]", param, re.IGNORECASE)
    n_match = re.match(r"[@]", param, re.IGNORECASE)

    if i_match: # Convert to list to index bits, then convert back to a string
        bol = list(bin_opcode)
        bol[7] = '1'
        bin_opcode = ''.join(bol)
        i_flag = False

    if n_match:
        bol = list(bin_opcode)
        bol[6] = '1'
        bin_opcode = ''.join(bol)
        n_flag = False

    # Check if neither n or i bits were set
    if n_flag and i_flag:
        bol = list(bin_opcode)
        bol[6] = '1'
        bol[7] = '1'
        bin_opcode = ''.join(bol)

    # Convert binary back into hex & strip leading zeroes
    n_opcode = dec2hex(int(bin_opcode, 2))
    n_opcode = n_opcode[4:]

    # Check to set xbpe bits
    xbpe = '0000'

    ta = None

    # Check for indexed mode.
    if 'X' in param.upper() and 'EXIT' not in param.upper():
        xbpe = '1000' # Set x bit
        for label, loc in label_dict.items():
            if label.strip(':') in param:   # Get label location and reg val
                ta = loc
                pc = base_val
                break

    # Check for octothorpe (#) sign (ta is going to be in hex)
    if not i_flag and n_flag: # Note: looks weird bc bools are reversed.
        if '#' in param: # Get target address
            loc = param.find('#')
        param_loc = param[loc+1:]
        ta = None
        # Check if target address is a label location
        for label, loc in label_dict.items():
            if param_loc == label.strip(':'):
                ta = loc
                break
        if not ta:
            ta = dec2hex(int(param_loc))

    elif i_flag and not n_flag: # indirect addressing mode
        loc = param.find('@')
        param_loc = param[loc+1:]
        for label, loc in label_dict.items():
            if param_loc == label.strip(':'):
                ta = loc
                break

    else: # Check for standard conversion of label address
        ta = param # Set label location

    # Calculate displacement (disp = target address - program counter)
    calculated_disp = hex2dec(ta) - hex2dec(pc)
    # Identify if pc-relative or based mode is needed (BASED HAS PRECEDENCE)
    # If address is >= base reg, use based

    if base_val != None and 0 < hex2dec(ta) < 4095 and hex2dec(ta) >= hex2dec(base_val) and base_flag:
        disp = str(hex2dec(ta) - hex2dec(base_val))
        while len(disp) < 3:
            disp = '0' + disp
        # Set b bit
        xbpe_l = list(xbpe)
        xbpe_l[1] = '1'
        xbpe = ''.join(xbpe_l)
        xbpe_h = dec2hex(int(xbpe, 2))[5:] # Convert to hex

        return n_opcode + xbpe_h + disp

    if -2048 < calculated_disp < 2047: # pc relative addressing
        if calculated_disp >= 0:
            disp = dec2hex(calculated_disp)[3:]
        else: # Handle negative w/ 2's complement
            disp = dec2hex(twoscomplement(calculated_disp))[3:]
        # Set p bit
        xbpe_l = list(xbpe)
        xbpe_l[2] = '1'
        xbpe = ''.join(xbpe_l)
        xbpe_h = dec2hex(int(xbpe, 2))[5:] # Convert to hex
    elif 0 < calculated_disp < 4095: # based mode calculation
        disp = dec2hex(calculated_disp)[3:]
        # Set p bit
        xbpe_l = list(xbpe)
        xbpe_l[1] = '1'
        xbpe = ''.join(xbpe_l)
        xbpe_h = dec2hex(int(xbpe, 2))[5:] # Convert to hex
    else: # Format 4 must be used                   # THIS IS WRONG AND MUST BE FIXED
        # Recall that format 4 isnt compatible with x or i bits
        if calculated_disp >= 0:
            xbpe_l = list(xbpe)
            xbpe_l[3] = '1'
            xbpe = ''.join(xbpe_l)
            xbpe_h = dec2hex(int(xbpe, 2))[5:]
            # Get displacement
            for label, loc in label_dict.items():
                if param == label.strip(':'):
                    disp = loc[3:]
                    break
            n_opcode = opcode
        else: # Handle negative format 4, according to sample assembler
            xbpe_l = list(xbpe)
            xbpe_l[1] = '1'
            xbpe = ''.join(xbpe_l)
            xbpe_h = dec2hex(int(xbpe, 2))[5:] # Convert to hex
            disp = '000'

    return n_opcode + xbpe_h + disp


def generate_format4(opcode, mnemonic, param, location, label_dict):
    '''
    Generate object code for format 4 instruction. Note that the B and P bits
    aren't used with format 4, they're just used with format 3 (Yay!).
    Instructions sent here should already be designated as format 4
    PARAMS:
        opcode:str: Instruction opcode
        mnemonic:str: Instruction mnemonic
        param:str: parameters of the given instruction
        location:str: hexadecimal location of the instruction
        label_dict:dictionary: dictionary containing labels and their locations
    RETURNS: obj_code:str: generated object code for the instruction
    '''
    # Convert opcode into binary to check N and I bits
    bin_opcode = bin(hex2dec(opcode))[2:]
    # If N and I bits arent used, they both must be set
    n_flag = True
    i_flag = True

    # Ensure we have 8 bits to work with
    while len(bin_opcode) != 8:
        bin_opcode = '0' + bin_opcode

    # Check for I and N bits being set. Note i and n bits affect opcode hexvalue
    i_match = re.match(r"[#]", param, re.IGNORECASE)
    n_match = re.match(r"[@]", param, re.IGNORECASE)

    if i_match: # Convert to list to index bits, then convert back to a string
        bol = list(bin_opcode)
        bol[7] = '1'
        bin_opcode = ''.join(bol)
        i_flag = False

    if n_match:
        bol = list(bin_opcode)
        bol[6] = '1'
        bin_opcode = ''.join(bol)
        n_flag = False

    # Check if neither n or i bits were set
    if n_flag and i_flag:
        bol = list(bin_opcode)
        bol[6] = '1'
        bol[7] = '1'
        bin_opcode = ''.join(bol)

    # Convert binary back into hex & strip leading zeroes
    n_opcode = dec2hex(int(bin_opcode, 2))
    n_opcode = n_opcode[4:]

    # Check x bit; E is going to be set by default (format 4), so rea
    xbpe = '0001'

    if 'X' in param.upper() and 'EXIT' not in param.upper():
        xbpe = '1001'

    xbpe = dec2hex(int(xbpe, 2))[5] # xbpe is just 4 bits
    xbpe_h = dec2hex(int(xbpe, 2))[5:] # Convert to hex

    # Now we check for the displacement location
    loc = param[1:]
    num_match = re.match("^[0-9]", loc, re.IGNORECASE)

    if num_match: # given integer
        disp = dec2hex(int(loc))[1:]
    else: # Check for label reference
        for label, loc in label_dict.items():
            if label.upper().strip(':') == param[1:].upper():
                disp = loc[1:] # get 20 bit label loc
                break
    # Construct and return generated object code
    return n_opcode + xbpe_h + disp


def pass2_parseline(line, label):
    '''
    Parse the given instruction into label, mnemonic, and parameter. If one of
    the previous fields do not exist, it is replaced with 'None'. Note that
    label is handled before the calling of this function.
    PARAMS:
        line:str: target line to parse
        label:str: label of the given line (can be NoneType)
    RETURNS:
        label:str: label of line, or NoneType if no label present
        mnemonic:str: mnemonic of line
        param:str: parameter of line, or NoneType if no parameter

    '''
    line = line.lstrip() # Space check for good measure
    #'Initialize' return variables (label already set prior to call)
    mnemonic = None
    param = None

    # Check for comment
    if len(line) > 0 and line[0] == '.':
        return None, None, None

    # Strip mnemonic
    mnemonic = re.match(r"([0-9A-Za-z+]*)( |\t|$)", line, re.IGNORECASE).group(0)
    mnemonic = mnemonic.rstrip()

    # Strip the parameter
    line = line.replace(mnemonic, '').lstrip()

    if mnemonic.upper() == 'BYTE': # Handle byte regex accordingly
        if line[0].upper() == 'C' or line[0].upper() == 'X':
            param = re.search("[CXcx0-9+](.+?)[']", line, re.IGNORECASE)
            param = param.group()

        else:
            param = re.search("[0-9+-](.+?)\w+(?:\s|$)", line, re.IGNORECASE)
            if param: #Get the parameter
                param = param.group().rstrip()
    else:

        # Check for comma indicating extra parameter
        if ',' in line:
            param = re.match(r"([0-9A-Za-z+@#\']*),([ ]*[0-9A-Za-z+@#\']*)(?:\s|$)", line, re.IGNORECASE).group(0).rstrip()
        else:
            param = re.match(r"([0-9A-Za-z+@#\',]*)(?:\s|$)", line, re.IGNORECASE).group(0).rstrip()
        #param = re.match(r"([0-9A-Za-z+@#\',]*)(?:\s|$)", line, re.IGNORECASE).group(0).rstrip()


    return label, mnemonic, param


def parseInstruction(line, location, label_dict, location_list):
    '''
    Parse instruction, and process output accordingly. Location/address of
    Instructions are updated in this function. More specifically, the label,
    mnemonic, and parameter of each line is parsed and processed.
    PARAMS:
        line:str: line to parse and process
        location:str: hexadecimal representation of current address
        label_dict:dictionary: dictionary containing labels and their locations
        location_list:list: list of all instruction locations
    RETURNS:
        location:str: hexadecimal representation of current location
        label_dict:dictionary: dictionary containing labels and their locations

    '''
    line = line.strip()

    # Match & output label lines
    match = re.match(r"([A-Z_][A-Z_0-9]*):", line, re.IGNORECASE)

    if match: # Process label line and handle output
        location, label, label_dict = parse_label_line(line, location, label_dict)
        location_list.append(label_dict[label])

    else: # Process standard line (no label present)
        location, output = parse_line(line, location, location_list)

    return location, label_dict


def parse_line(line, location, location_list):
    '''
    Parse and process the given line. Note that this line will not contain a
    label, thus not produce an output. Given the design of parseInstruction,
    we will just return 'None' in the place of output. Location
    will be updated in this function.
    PARAMS:
        line:str: line to parse and process
        location:str: hexadecimal representation of current program location
    RETURNS:
        location:str: current location in hexadecimal format (updated)
        output:None: Nil value
    '''
    location_list.append(location)
    line = line.lstrip() # Space check for good measure

    # Check for comment
    if len(line) > 0 and line[0] == '.':
        return location, None

    # Strip label based on colon pos
    pos = line.find(':')
    label = line[0:pos+1]

    if line.upper() == 'END':       # Just return if we encounter end
        return location, None

    # Strip mnemonic
    try:
        mnemonic = re.match(r"([0-9A-Za-z+]*)( |\t|$)", line, re.IGNORECASE).group(0)
        mnemonic = mnemonic.rstrip()
    except AttributeError:
        raise SystemExit("Invalid mnemonic at label: " + label)

    # Strip the parameter
    line = line.replace(mnemonic, '').lstrip()

    if mnemonic.upper() == 'BYTE': # Handle byte regex accordingly
        if line[0].upper() == 'C' or line[0].upper() == 'X':
            param = re.search("[CXcx0-9+](.+?)[']", line, re.IGNORECASE)
            param = param.group()

        else:
            param = re.search("[0-9+-](.+?)\w+(?:\s|$)", line, re.IGNORECASE)

            if param: #Get the parameter
                param = param.group()
            else:
                return location, None
    else:
        param = re.match(r"[0-9A-Za-z+@#\']*", line, re.IGNORECASE).group(0).rstrip()

    # Check for forward reference or end. Otherwise, just update location
    if mnemonic.upper() == 'START':
        location = initialize_location(int(param))
    elif mnemonic.upper() == 'END':
        return location, None
    else:
        location = calculate_location(mnemonic, param, location, line)

    return location, None


def parse_label_line(line, location, label_dict):
    '''
    Parse and process the given line. This function will separate the line and
    create variables for the label, mnemonic, and parameter fields. NOTE:
    This function is used specifically to process lines with labels. Location
    also updated.
    PARAMS:
        line:str: line to parse
        location:str: current location in file (hex)
        label_dict:dictionary: dictionary containing labels and their locations
    RETURNS
        location:str: current location in hexadecimal format
        label:str: String containing label name (with colon)
        label_dict:dictionary: dictionary containing labels and their locations
    '''
    prev_location = location

    line = line.lstrip() # Space check for good measure

    # Strip label based on colon pos
    pos = line.find(':')
    label = line[0:pos+1]

    # Grab the label and prepare line for further processing
    label = label.upper()
    line = line[pos+1:].lstrip() # Strip off label and leading whitespace

    # Check for a duplicate label
    for found_label, val in label_dict.items():
        if label == found_label:
            raise SystemExit(f"Previously Defined Symbol: {label}")

    label_dict[label] = location # Add the label to label list for pass1

    if line.upper() == 'END':       # Just return if we encounter end
        return location, None, label_dict

    # Strip mnemonic
    try:
        mnemonic = re.match(r"([0-9A-Za-z+]*)( |\t|$)", line, re.IGNORECASE).group(0)
        mnemonic = mnemonic.rstrip()
    except AttributeError:
        raise SystemExit("Invalid mnemonic at label: " + label)

    # Check for number leading mnemonic
    if mnemonic:
        num_check = re.match("^[0-9]", mnemonic, re.IGNORECASE)
        if num_check:
            raise SystemExit(f"Expected instruction mnemonic at '{label}':\n{line}")

    # Strip parameter
    line = line.replace(mnemonic, '').lstrip()

    if mnemonic.upper() == 'BYTE': # Handle byte regex accordingly
        # Check for character byte or hex byte

        if line[0].upper() == 'C' or line[0].upper() == 'X':
            param = re.search("[CXcx0-9+-](.+?)[']", line, re.IGNORECASE)
            param = param.group()

        else: # Identify byte parameter (expecting an integer)
            param = re.search("^[0-9+-]", line, re.IGNORECASE)
            if param: #Get the parameter
                param = param.group()
            else:
                return location, None, label_dict
    else:
        param = re.match(r"[0-9A-Za-z+@#\']*", line, re.IGNORECASE).group(0).rstrip()

    # Generate hex address for instruction
    if mnemonic.upper() == 'START': # Check to set starting location
        location = initialize_location(int(param))
    else:
        location = calculate_location(mnemonic, param, location, line) # Update location

    return location, label, label_dict


def calculate_location(mnemonic, param, location, line):
    '''
    Identify the size of the instruction's mnemonic/directive/parameters,
    and update the location accordingly. Extended instructions are 4 bytes,
    regular format 3 instructions are 3 bytes, format 2 is 2 bytes, etc.
    PARAMS:
        mnemonic:str: mnemonic/directive to identify
        param:str: parameter field of instruction.
        location:str: hexadecimal representation of current location
        line:str: Entirety of the current line. Used for errors
    RETURNS: location:str: hexadecimal representation of current location.
    '''

    location = hex2dec(location)
    # identify if mnemonic or directive, and update location
    for md, size in instructions.items(): # Where md = mneum/dir
        if mnemonic.upper() == md:
            location += size

    for instruction in extended_instructions: #Check extended instructions
        if mnemonic.upper() == instruction.upper():
            location += 4

    for directive in directives:
        if mnemonic.upper() == directive.upper():
            # Identify what directive we are working with & process location
            if mnemonic.upper() == 'BYTE':

                # Make sure syntax is legal
                param_match = re.match(r"[CX0-9]", param, re.IGNORECASE)
                if param_match:
                    location = calc_byte_dir(param, location, line)
                elif param[0] == '+' or param[0] == '-':
                    location += 1

            elif mnemonic.upper() == 'RESB':
                #for byte reservation, add to location
                location += int(param)

            elif mnemonic.upper() == 'RESW':
                # A word in SIC/XE is 3 bytes.
                location += (int(param) * 3)
            elif mnemonic.upper() == 'BASE':
                pass
            elif mnemonic.upper() == 'NOBASE':
                pass
            elif mnemonic.upper() == 'WORD':
                location += 3

    location = dec2hex(location)

    return location


def calc_byte_dir(param, location, line):
    '''
    calculate the bytes within the passed parameter. This function will also
    handle identifying whether or not we deal with hex or character bytes (X/C).
    Side note: dir = directive
    PARAMS:
        param:str: parameter string parsed from instruction
        location:int: decimal representation of current program location
        line:str: string containing entirety of the current line
    RETURNS:
        location:int: updated location with respect to directive's parameter
    '''

    if param[0].upper() == 'C': # Character bytes
        # Get length of char bytes
        q_loc = param.find('\'') + 1
        param = param[q_loc:]
        q_loc = q_loc = param.find('\'')
        param = param[:q_loc]
        #Update location
        location += len(param)
        return location

    elif param[0].upper() == 'X': # Hex bytes
        # Get length of hex bytes
        q_loc = param.find('\'') + 1
        param = param[q_loc:]
        q_loc = q_loc = param.find('\'')
        param = param[:q_loc]
        # Hex bytes are 2 chars long, so div by 2. Note: we round up.
        # To minimize improted libraries, I'm using modulus
        result = (len(param) // 2) + (len(param) % 2 > 0)
        location += result
        return location
    else:
        # Check for raw number
        match_num = re.match(r"^[0-9]", param)
        if match_num:
            location += 1
            return location
        else:
            return location


def initialize_location(num):
    '''
    Initialize starting location/address of the file. This is only run as a
    result of encountering the 'START' directive. Address converted into hex.
    PARAMS: num:int: decimal number to set as starting address
    RETURNS: address:str: hexadecimal starting address for program
    '''
    address = str(num)
    while len(address) != 6:
        address = '0' + address
    return address


def twoscomplement(value):
    '''
    Calculate two's complement of a given integer, and return the value.
    Note that we are performing this operation with 12 bits.
    PARAMS: value:int: decimal representation of target number
    RETURNS: twos:int: return the decimal representation of value's 2's complement
    '''
    # Get binary digits of value
    binary = bin(abs(value))[2:]
    while len(binary) != 12:
        binary = '0'+ binary
    # Listify and flip bits
    binary_l = list(binary)

    for index in range(len(binary_l)):
        if binary_l[index] == '1':
            binary_l[index] = '0'
        elif binary_l[index] == '0':
            binary_l[index] = '1'

    new_binary = ''.join(binary_l)
    # Add 1 to obtain 2's complement
    twos = bin(int(new_binary, 2) + 1)[2:]
    return int(twos, 2)


def dec2hex(num):
    '''
    Convert decimal number to 6 byte hexadecimal number
    PARAMS: num:int: number to convert to hex
    RETURNS: hex:str: converted hex value of num
    '''
    # Convert to hex and strip off 0x
    num = hex(num)
    loc = num.find('x')
    num = num[loc+1:]
    num = num.upper()

    # Check if num is 6 bytes long
    if len(num) == 6:
        return num
    else:
        while len(num) != 6: # Make num 6 bytes long
            num = '0'+num
        return num


def hex2dec(hex):
    '''
    Convert 6 byte hexadecimal number into a decimal number
    PARAMS: hex:str: 6 byte hexadecimal string to convert
    RETURNS: num:int: converted decimal number from hex
    '''
    return int(hex, 16)


if __name__ == "__main__":
    start()
