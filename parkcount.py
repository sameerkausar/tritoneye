def parkCount(hill,direction,totalCars,potentialSpots):
	if(direction == 1 ): ## car entered
		#means hill=1 car goes 1->2
		totalCars[hill] = totalCars[hill] - 1
		totalCars[hill+1] = totalCars[hill+1] + 1
	else:
		#means hill=1 car goes 2->1
		totalCars[hill] = totalCars[hill] + 1
		totalCars[hill+1] = totalCars[hill+1] - 1
	print totalCars
	openSpots = []
	first = True #do something different for index 0 aka total car count
 	for s, c in zip(potentialSpots, totalCars):
 		if first:
 			c = -c
 			first = False
		if s+c < 0:
			openSpots.append(0)
		else:
			openSpots.append(s-c)
	
	print openSpots

def main():
	## if hill = 0, car entered lot
	testCase = ["01","01","11","21","01","20","10","01","01","11"]
	count = 0
	##10 open spots per floor, 5 floors, index 0 is total cars
	potentialSpots = [50,10,10,10,10,10]
	totalCars = [0,0,0,0,0,0]

	while count < len(testCase):
		hill = str(testCase[count])[0]
		hill = int(hill)
		direction = str(testCase[count])[1]
		#print direction
		direction = int(direction)
		parkCount(hill,direction,totalCars,potentialSpots)
		count += 1

main()
