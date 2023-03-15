from tcspy.pilot import StartUp
import sys
unitnum = int(sys.argv[1])
startup = StartUp(unitnum =unitnum)
startup.run()