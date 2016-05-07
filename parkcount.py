## if hill = 0, car entered lot
testCase = ["01","01","11","21","01","20","10"]
count = 0
##10 open spots per floor, 5 floors, index 0 is total cars
spots = [0,10,10,10,10,10]

while count < len(testCase):
	hill = str(testCase[count])[0]
	hill = int(hill)
	direction = str(testCase[count])[1]
	#print direction
	direction = int(direction)
	if(direction == 1 ): ## car entered
		#means hill=1 car goes 1->2
		spots[hill+1] = spots[hill+1] - 1
		spots[hill] = spots[hill] + 1
	else:
		#means hill=1 car goes 2->1
		spots[hill] = spots[hill] - 1
		spots[hill+1] = spots[hill+1] + 1
	count = count+1
	print spots
