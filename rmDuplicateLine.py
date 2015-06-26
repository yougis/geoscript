try:
    from osgeo import osr, ogr, gdal
except ImportError:
    import osr, ogr, gdal

import sys
#############################################################################
# Argument processing.

infilename = None
outfilename = None

argv = gdal.GeneralCmdLineProcessor( sys.argv )
if argv is None:
    sys.exit( 0 )

i = 1
while i < len(argv):
	arg = argv[i]
	if infilename is None:
		infilename = arg
	elif outfilename is None:
		outfilename = arg
	i = i + 1

#############################################################################
# remove duplicate line

lines_seen = set() # holds lines already seen
outfile = open(outfilename, "w")
for line in open(infilename, "r"):
    if line not in lines_seen: # not a duplicate
        outfile.write(line)
        lines_seen.add(line)
outfile.close()
