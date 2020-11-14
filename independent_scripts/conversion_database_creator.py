#!/usr/bin/env python

"""
########################################################################
# Author:       Carlos A. Ruiz Perez
# Email:        cruizperez3@gatech.edu
# Intitution:   Georgia Institute of Technology
# Version:      0.9
# Date:         October 05, 2020

# Description: Downloads the information necessary to create interconversion of
# accessions and appends it into the MicrobeAnnotator database.
########################################################################
"""

################################################################################
"""---0.0 Import Modules---"""
import wget
from shutil import copyfileobj
from pathlib import Path
import urllib.request
import gzip

################################################################################
"""---1.0 Define Functions---"""
def create_refseq_to_uniprot(input_table, database_to_append, keep):
    # Connect to database
    conn = sqlite3.connect(database_to_append)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS refseq_to_uniprot")
    cursor.execute('CREATE TABLE refseq_to_uniprot \
        (refseq_id TEXT, uniprot_id TEXT)')
    # Read input table and create table within SQLite database
    with open(input_table, 'r') as refseq_conversion:
        record_counter = 0
        records = []
        for line in refseq_conversion:
            # Commit changes after 500000 records
            if record_counter == 500000:
                cursor.execute("begin")
                cursor.executemany('INSERT INTO refseq_to_uniprot VALUES(?, ?)', records)
                cursor.execute("commit")
                record_counter = 0
                records = []
            else:
                line = line.strip('\n').split("\t")
                records.append((line[1], line[0]))
                record_counter += 1
        # Commit remaining records
        if record_counter > 0:
            cursor.execute("begin")
            cursor.executemany('INSERT INTO refseq_to_uniprot VALUES(?, ?)', records)
            cursor.execute("commit")
        # Create index for faster access
        cursor.execute('CREATE INDEX refseq_index ON refseq_to_uniprot (refseq_id)')
    # Remove temporal files
    if keep == False:
        if Path(input_table).is_file():
            Path(input_table).unlink()

def create_ko_to_ec(output_folder, database, keep):
    # Download information
    download_output = output_folder + "/02.KO_to_EC_identifiers.txt.gz"
    wget.download("http://enve-omics.ce.gatech.edu/data/public_microbeannotator/02.KO_to_EC_identifiers.txt.gz",
                            out=download_output)
    # Connect with database
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    # Create table with correspondence KO -> EC
    cursor.execute("DROP TABLE IF EXISTS ko_to_ec")
    cursor.execute('CREATE TABLE ko_to_ec \
        (ko_identifier TEXT, ec_identifier TEXT)')
    with gzip.open(download_output, 'rt') as ko_conversion:
        record_counter = 0
        records = []
        for line in ko_conversion:
            # Commit changes after 500000 records
            if record_counter == 500000:
                cursor.execute("begin")
                cursor.executemany('INSERT INTO ko_to_ec VALUES(?, ?)', records)
                cursor.execute("commit")
                record_counter = 0
                records = []
            else:
                line = line.strip('\n').split("\t")
                records.append((line[0], line[1]))
                record_counter += 1
        # Commit remaining records
        if record_counter > 0:
            cursor.execute("begin")
            cursor.executemany('INSERT INTO refseq_to_uniprot VALUES(?, ?)', records)
            cursor.execute("commit")
        # Create index for faster access
        cursor.execute('CREATE INDEX ko_id ON ko_to_ec (ko_identifier)')
    # Create table with correspondence EC -> KO
    cursor.execute("DROP TABLE IF EXISTS ec_to_ko")
    cursor.execute('CREATE TABLE ec_to_ko \
        (ec_identifier TEXT, ko_identifier TEXT)')
    with gzip.open(download_output, 'rt') as ko_conversion:
        record_counter = 0
        records = []
        for line in ko_conversion:
            # Commit changes after 500000 records
            if record_counter == 500000:
                cursor.execute("begin")
                cursor.executemany('INSERT INTO ec_to_ko VALUES(?, ?)', records)
                cursor.execute("commit")
                record_counter = 0
                records = []
            else:
                line = line.strip('\n').split("\t")
                records.append((line[1], line[0]))
                record_counter += 1
        # Commit remaining records
        if record_counter > 0:
            cursor.execute("begin")
            cursor.executemany('INSERT INTO ec_to_ko VALUES(?, ?)', records)
            cursor.execute("commit")
        # Create index for faster access
        cursor.execute('CREATE INDEX ec_id ON ec_to_ko (ec_identifier)')
    # Remove temporal files
    if keep == False:
        if Path(download_output).is_file():
            Path(download_output).unlink()
    
def create_interpro_tables(output_folder, database, keep):
    # Download information
    download_output = output_folder + "/interpro_metadata.xml.gz"
    wget.download("ftp://ftp.ebi.ac.uk/pub/databases/interpro/interpro.xml.gz",
                            out=download_output)
    interpro_to_ec = {}
    interpro_to_ko = {}
    # Parse file information into dictionaries to merge into the SQLite database
    with gzip.open(download_output, 'rt') as infile:
        interpro_id = ""
        ec_identifier = []
        ko_identifier = []
        for line in infile:
            if line.startswith("<interpro id="):
                interpro_id = line.strip().split('"')[1]
            elif "db_xref" in line and "EC" in line:
                identifier = line.strip().split('"')[3]
                ec_identifier.append(identifier)
            elif "db_xref" in line and "KEGG" in line:
                identifier = line.strip().split('"')[3]
                ko_identifier.append(identifier)
            elif line.startswith("</interpro>"):
                interpro_to_ec[interpro_id] = ec_identifier
                interpro_to_ko[interpro_id] = ko_identifier
                interpro_id = ""
                ec_identifier = []
                ko_identifier = []
    # Connect with the database
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    # Create table with correspondence InterPro -> KO
    cursor.execute("DROP TABLE IF EXISTS interpro_to_ko")
    cursor.execute('CREATE TABLE interpro_to_ko \
        (interpro_id TEXT, ko_identifier TEXT)')
    record_counter = 0
    records = []
    for interproscan, ko_id in interpro_to_ko.items():
        for element in ko_id:
            # Commit changes after 500000 records
            if record_counter == 500000:
                cursor.execute("begin")
                cursor.executemany('INSERT INTO interpro_to_ko VALUES(?, ?)', records)
                cursor.execute("commit")
                record_counter = 0
                records = []
            else:
                records.append((interproscan, element))
                record_counter += 1
        # Commit remaining records
        if record_counter > 0:
            cursor.execute("begin")
            cursor.executemany('INSERT INTO interpro_to_ko VALUES(?, ?)', records)
            cursor.execute("commit")
        # Create index for faster access
        cursor.execute('CREATE INDEX inter_id ON interpro_to_ko (interpro_id)')
    
    # Create table with correspondence InterPro -> EC
    cursor.execute("DROP TABLE IF EXISTS interpro_to_ec")
    cursor.execute('CREATE TABLE interpro_to_ec \
        (interpro_id TEXT, ec_identifier TEXT)')
    record_counter = 0
    records = []
    for interproscan, ec_id in interpro_to_ec.items():
        for element in ec_id:
            # Commit changes after 500000 records
            if record_counter == 500000:
                cursor.execute("begin")
                cursor.executemany('INSERT INTO interpro_to_ec VALUES(?, ?)', records)
                cursor.execute("commit")
                record_counter = 0
                records = []
            else:
                records.append((interproscan, element))
                record_counter += 1
        # Commit remaining records
        if record_counter > 0:
            cursor.execute("begin")
            cursor.executemany('INSERT INTO interpro_to_ec VALUES(?, ?)', records)
            cursor.execute("commit")
        # Create index for faster access
        cursor.execute('CREATE INDEX inter_id ON interpro_to_ec (interpro_id)')
    
    # Create table with correspondence KO -> InterPro
    cursor.execute("DROP TABLE IF EXISTS ko_to_interpro")
    cursor.execute('CREATE TABLE ko_to_interpro \
        (ko_identifier TEXT, interpro_id TEXT)')
    record_counter = 0
    records = []
    for interproscan, ko_id in interpro_to_ko.items():
        for element in ko_id:
            # Commit changes after 500000 records
            if record_counter == 500000:
                cursor.execute("begin")
                cursor.executemany('INSERT INTO ko_to_interpro VALUES(?, ?)', records)
                cursor.execute("commit")
                record_counter = 0
                records = []
            else:
                records.append((element, interproscan))
                record_counter += 1
        # Commit remaining records
        if record_counter > 0:
            cursor.execute("begin")
            cursor.executemany('INSERT INTO ko_to_interpro VALUES(?, ?)', records)
            cursor.execute("commit")
        # Create index for faster access
        cursor.execute('CREATE INDEX ko_id ON ko_to_interpro (ko_identifier)')

    # Create table with correspondence KO -> InterPro
    cursor.execute("DROP TABLE IF EXISTS ec_to_interpro")
    cursor.execute('CREATE TABLE ec_to_interpro \
        (ec_identifier TEXT, interpro_id TEXT)')
    record_counter = 0
    records = []
    for interproscan, ec_id in interpro_to_ec.items():
        for element in ec_id:
            # Commit changes after 500000 records
            if record_counter == 500000:
                cursor.execute("begin")
                cursor.executemany('INSERT INTO ec_to_interpro VALUES(?, ?)', records)
                cursor.execute("commit")
                record_counter = 0
                records = []
            else:
                records.append((element, interproscan))
                record_counter += 1
        # Commit remaining records
        if record_counter > 0:
            cursor.execute("begin")
            cursor.executemany('INSERT INTO ec_to_interpro VALUES(?, ?)', records)
            cursor.execute("commit")
        # Create index for faster access
        cursor.execute('CREATE INDEX ec_id ON ec_to_interpro (ec_identifier)')

    # Remove temporal files
    if keep == False:
        if Path(download_output).is_file():
            Path(download_output).unlink()

################################################################################
"""---2.0 Main Function---"""

def main():
    import argparse, sys
    # Setup parser for arguments.
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
            description='''This script build the search databases required by MicrobeAnnotator\n'''
            '''Usage: ''' + sys.argv[0] + ''' -f [output_file folder]\n'''
            '''Global mandatory parameters: -f [output_file folder]\n'''
            '''Optional Database Parameters: See ''' + sys.argv[0] + ' -h')
    parser.add_argument('-i', '--input_table', dest='intable', action='store', required=True,
                        help='RefSeq to Uniprot table to create correspondence table.')
    parser.add_argument('-d', '--database', dest='database', action='store', required=True,
                        help='SQLite database to create tables in.')
    parser.add_argument('-o', '--output', dest='output', action='store', required=True,
                        help='Output directory where data should be stored.')
    parser.add_argument('--keep', dest='keep', action='store_true', required=False,
                        help='Keep intermediate files, can increase disk requirement (not necessary and therefore not recommended).')
    args = parser.parse_args()

    intable = args.intable
    database = args.database
    output = args.output
    keep = args.keep

    # ----------------------------
    print("Creating correspondence tables...")
    create_refseq_to_uniprot(intable, database, keep)
    create_ko_to_ec(output, database, keep)
    create_interpro_tables(output, database, keep)
    print("Done!")
    # ----------------------------

if __name__ == "__main__":
    main()

