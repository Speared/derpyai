# Take a file as an argument, trim trailing whitespace off each line
import sys

args = sys.argv[1:]
for arg in args:
    try:
        file = open(arg, 'r')
        new_file = ""
        for line in file:
            new_file += line.rstrip() + '\n'
        file.close()
        file = open(arg, 'w')
        file.write(new_file)
        file.close()
    except IOError:
        print arg, "not found"
