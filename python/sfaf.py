#!/usr/bin/env python
"""Use a SFAF CSV metadata dictionary to parse a SFAF file parameter into Python 
   dictionary output using callbacks to enable very large files."""

import argparse
import csv
import math
import pprint
import re
import types
from pathlib import Path

__author__ = "Eric Lindahl"
__copyright__ = "Copyright 2012, Sciumo, Inc"
__credits__ = ["Eric Lindahl"]
__license__ = "LGPL"
__version__ = "0.0.2"
__maintainer__ = "Eric Lindahl"
__email__ = "eric.lindahl.tab@gmail.com"
__status__ = "Alpha"


cwd = Path.cwd()
mod_path = Path(__file__).parent
DEFAULTSFAF = (mod_path / "../MCEBPub7.csv").resolve()
Metadata = None
cur_line = 0
pp = pprint.PrettyPrinter(indent=4)
LONGOPTIONS = ["format=", "batch=", "csv="]

parser = argparse.ArgumentParser(
    prog="SFAF Parser", description="Parse a SFAF file into text or create csv file."
)
parser.add_argument("filename", help="name of SFAF input file")
parser.add_argument(
    "-c", "--csv", help="input csv file name if you want to write to a csv"
)
parser.add_argument(
    "-b",
    "--batch",
    help="if you wish to print in batches, input number - does not work with csv",
)
parser.add_argument(
    "-f", "--format", help="input name of format file if not using default"
)


def integer(s_):
    """Parse a string to an Integer or None on error"""
    try:
        return int(s_)
    except ValueError:
        return None


def dmsToDD(dms_):
    """DMS to degrees dictionary update"""
    sign = 1.0
    if dms_["dir"] == "S" or dms_["dir"] == "W":
        sign = -1.0
    dd = dms_["min"] * 60.0 + dms_["sec"]
    dd = sign * (dms_["deg"] + dd / 3600.0)
    return dd


def latI180(dms_):
    """Normalize dms_.lat.dec into 180.0 degrees"""
    lat = math.floor(dms_["lat"]["dec"] + 90.0)
    return lat


# Regular expression for DMS
regDMS = re.compile(
    "([0-9]{2})([0-9]{2})([0-9X]{2})([nsNS])([0-9]{3})([0-9]{2})([0-9X]{2})([ewEW])"
)


def parseDMS(str_):
    """Parse a DMS string and return a dictionary with DMS and deg entries"""
    mdms = regDMS.match(str_)
    if mdms is None:
        print("!error parse DMS :" + str_)
        return None
    d = mdms.groups()
    seclat = d[2].replace("X", "0")
    seclon = d[6].replace("X", "9")
    latlon = {
        "lat": {
            "deg": integer(d[0]),
            "min": integer(d[1]),
            "sec": integer(seclat),
            "dir": d[3].upper(),
        },
        "lon": {
            "deg": integer(d[4]),
            "min": integer(d[5]),
            "sec": integer(seclon),
            "dir": d[7].upper(),
        },
    }

    latlon["lat"]["dec"] = dmsToDD(latlon["lat"])
    latlon["lon"]["dec"] = dmsToDD(latlon["lon"])
    return latlon


# Rechandlers registry for specific SFAF specific handlers.
recHandlers = {}

# Frequency multiples for normalizing frequency to megahertz
freqMultiple = {"K": 0.001, "M": 1.0, "G": 1000.0, "T": 1000000.0}

regCenterF = re.compile("([KMGT])([\.0-9]+)")
regBand = re.compile("([KMGT])([\.0-9]+)\-([KMGT])([\.0-9]+)")
regDefBand = re.compile("([KMGT])([\.0-9]+)\-([\.0-9]+)")
regRejF = re.compile("([KMGT])([\.0-9]+)\(([\.0-9]+)\)")


def onHandleFreqMulti(rec_, isArray, recNum_, recSup_, recVal_):
    band = regDefBand.match(recVal_)
    if band is None:
        return None
    d = band.groups()

    mult = freqMultiple[d[0]]
    res = [str(mult * float(d[1])), str(mult * float(d[2]))]

    # b = 1
    # while 	str(recNum_) + "_" + str(b) + "_band" in rec_.keys():
    # b = b + 1
    # recId = str(recNum_) + "_" + str(b) + "_band"
    recId = str(recNum_) + "_band"
    if isArray:
        if recId not in rec_.keys():
            rec_[recId] = []
        rec_[recId].append(res)
    else:
        rec_[recId] = res
    return res


def onHandleDouble(rec_, isArray, recNum_, recSup_, recVal_):
    try:
        val = float(recVal_)
        if val is not None:
            recId = str(recNum_)
            rec_[recId] = str(val)
            return val
    except:
        return None
    return None


def onHandleFreq(rec_, isArray, recNum_, recSup_, recVal_):
    band = regBand.match(recVal_)
    if band is None:
        band = regDefBand.match(recVal_)
        if band is None:
            freq = regRejF.match(recVal_)
            if freq is None:
                freq = regCenterF.match(recVal_)
                if freq is None:
                    return None
            d = freq.groups()
            recId = str(recNum_) + "_freq"
            res = freqMultiple[d[0]] * float(d[1])
            if len(d) > 2:
                rejRecId = str(recNum_) + "_rej_freq"
                rec_[rejRecId] = freqMultiple[d[0]] * float(d[2])
        else:
            d = band.groups()
            recId = str(recNum_) + "_band"
            mult = freqMultiple[d[0]]
            res = str(mult * float(d[1])) + ", " + str(mult * float(d[2]))
            # print recNum_, recVal_, recId, res

        rec_[recId] = res
    else:
        d = band.groups()
        recId = str(recNum_) + "_band"
        # res = [freqMultiple[d[0]] * float(d[1]),freqMultiple[d[2]] * float(d[3])]
        res = (
            str(freqMultiple[d[0]] * float(d[1]))
            + ", "
            + str(freqMultiple[d[2]] * float(d[3]))
        )
        rec_[recId] = res
        # print recNum_, recVal_, recId, res

    return res


def onHandleDMS(rec_, isArray, recNum_, recSup_, recVal_):
    try:
        recId = str(recNum_) + "_ll"
        res = parseDMS(recVal_)
        rec_[recId] = str(res["lat"]["dec"]) + "," + str(res["lon"]["dec"])
        return res
    except:
        print("Error on DMS parse:" + recVal_ + " Line:" + str(cur_line))
        return None


recHandlers[110] = onHandleFreq
recHandlers[111] = onHandleFreqMulti
recHandlers[303] = onHandleDMS
recHandlers[306] = onHandleDouble
recHandlers[403] = onHandleDMS

p7line = re.compile("([0-9]+)(\/([0-9]+))?\s*\.\s*(.*)")


def parsep7(line_, lastRec, lastRecNum, fmts_):
    mrec = p7line.match(line_)
    if mrec is None:
        print("No Match Fail on:'" + line_ + "'" + "Line:" + str(cur_line))
        return None
    groups = len(mrec.groups())
    if groups < 4:
        print("Fail groups on: " + line_ + "Line:" + str(cur_line))
        return None
    rec = {}
    recVal = mrec.group(4)
    recNum = integer(mrec.group(1))
    recSup = mrec.group(3)
    fmt = ["000", "Unknown", "UNK", "", "", "", "", "", "FALSE", str(recNum)]

    if recNum not in fmts_.keys():
        print("!!No format for: ", recNum)
    else:
        fmt = fmts_[recNum]
    recId = fmt[9]

    if recNum < 10 and recNum < lastRecNum:
        rec[recId] = recVal
        return rec, lastRec, recNum, True

    isArray = not (fmt[8] == "FALSE")

    if recSup is not None and len(recSup) > 0:
        recSup = integer(recSup)

    if isArray:
        recsuplist = []
        if recId not in lastRec.keys():
            lastRec[recId] = recsuplist
        else:
            lastRecVal = lastRec[recId]
            if not isinstance(lastRecVal, list):
                recsuplist.append(lastRecVal)
                lastRec[recId] = recsuplist
            else:
                recsuplist = lastRecVal

            # if type(lastRecVal) is not list:
            #     recsuplist.append(lastRecVal)
            #     lastRec[recId] = recsuplist
            # else:
            #     recsuplist = lastRecVal

        recsuplist.append(recVal)
    else:
        if recId in lastRec.keys():
            if recNum != 5:
                lastRec[recId] = lastRec[recId] + "\n" + recVal
            else:
                lastRec[recId] = recVal
        else:
            lastRec[recId] = recVal

    if recNum in recHandlers.keys():
        # print "Rec handler", recNum
        recHandler = recHandlers[recNum]
        if isinstance(recHandler, types.FunctionType):
            recHandler(lastRec, isArray, recNum, recSup, recVal)
    return rec, lastRec, recNum, False


def readSFAFFormats(argv_, file_=DEFAULTSFAF):
    """Read SFAF column format information"""
    # optlist, _ = getopt.getopt(argv_, "", LONGOPTIONS)
    fmtfile = file_

    # for opt, arg in optlist:
    #     if opt == "--format":
    #         fmtfile = arg

    if argv_.format is not None:
        fmtfile = argv_.format

    sfmts = {}
    with open(fmtfile) as csvfile:
        fmts = csv.reader(csvfile, dialect="excel", delimiter=",")
        next(fmts)  # skip header
        for fmt in fmts:
            code = integer(fmt[0])
            if code is None:
                print("Error: Unknown format:", fmt)
            else:
                sfmts[code] = fmt
    return sfmts


def recprint(recs_, cnt_):
    """Print all records"""
    pp.pprint(recs_)


def readAllRecs(file_, fmts_, batch=10000, callback=recprint):
    global cur_line
    recs = []
    # fileid = "sfaf:" + file_
    cnt = 1
    cur_line = 0
    with open(file_) as f:
        lastRec = {}
        lastRecNum = 0
        for line in f:
            cur_line = cur_line + 1
            rec, lastRec, lastRecNum, isnew = parsep7(line, lastRec, lastRecNum, fmts_)
            if isnew:
                # print rec
                # recid = fileid + "_" + str(cnt)
                # lastRec["id"] = recid
                recs.append(lastRec)
                cnt = cnt + 1
                lastRec = rec
                if cnt % batch == 0:
                    callback(recs, cnt)
                    recs = []
                    # recid = fileid + "_" + str(cnt)
        # recid = fileid + "_" + str(cnt)
        # lastRec["id"] = recid
        recs.append(lastRec)
        # callback(recs, cnt)
    return recs


sfaf_fmts = {}


def readSFAFRecs(argv_, fmts_, callback_=recprint, batch_=1000):
    save_csv = False

    if argv_.batch is not None:
        batch_ = argv_.batch
    if argv_.csv is not None:
        save_csv = True
        filename_ = argv_.csv

    infile = argv_.filename

    recs = readAllRecs(infile, fmts_, batch_, callback_)
    if save_csv:
        write_csv(recs, fmts_, filename_)
    return recs, fmts_


def readSFAF(argv_, callback_=recprint, batch_=1000):
    """Read all records from file using SFAF format CSV for column information.
    Batch the results and call callback every batch records and flush to limit memory.
    """
    cur_line = 0
    sfaf_fmts = readSFAFFormats(argv_)
    return readSFAFRecs(argv_, sfaf_fmts, callback_, batch_)


header_key = re.compile("([0-9]+)(\w*)")


def swap_name(old_name, fmts_):
    a_match = header_key.findall(old_name)
    num = a_match[0][0]
    rest = a_match[0][1]
    if rest == "":
        return "_".join(fmts_[integer(num)][0:3])
    else:
        return "_".join([*fmts_[integer(num)][0:3], rest])


def write_csv(list_of_dicts, fmts_, filename):
    for a_dict in list_of_dicts:
        for key in list(a_dict.keys()):
            a_dict[swap_name(key, fmts_)] = a_dict.pop(key)

    all_keys = set().union(*(d.keys() for d in list_of_dicts))
    sorted_keys = sorted(all_keys, key=lambda x: integer(header_key.findall(x)[0][0]))

    with open(filename, "w", newline="") as csvfile:
        my_writer = csv.DictWriter(
            csvfile, delimiter=",", fieldnames=sorted_keys, extrasaction="ignore"
        )
        my_writer.writeheader()
        my_writer.writerows(list_of_dicts)


if __name__ == "__main__":
    readSFAF(parser.parse_args())
