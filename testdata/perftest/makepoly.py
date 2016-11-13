


def makepolygon(mystring):
	coords = mystring.split()
	coords = [ coord.split(',') for coord in coords ]
			
	coordinates = [ "{} {}".format(item[0],item[1]) for item in coords ]

	return "POLYGON((" + ",".join(coordinates) + "))"