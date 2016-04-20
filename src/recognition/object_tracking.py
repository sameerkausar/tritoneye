import cv2
import imutils
import numpy as np
import math 
import operator
from collections import deque
import recognition.recognition_conf as conf

# --------------------------------------------------
# Image processing algorithm switcher
bs_selector = { # Background subtration
	conf.BackgroundSubtractor.MOG:	lambda: cv2.bgsegm.createBackgroundSubtractorMOG(), # parameter example: (200, 5, 0.5, 0)
	conf.BackgroundSubtractor.MOG2:	lambda: cv2.createBackgroundSubtractorMOG2(),
	conf.BackgroundSubtractor.GMG:	lambda: cv2.bgsegm.createBackgroundSubtractorGMG(),
}

blur_selector = { # Blur method to fill gaps between close contours
	conf.GapFillingMethod.MEDIAN:		lambda frame: cv2.medianBlur(frame, 5),
	conf.GapFillingMethod.BILATERAL:	lambda frame: cv2.bilateralFilter(frame, 9, 75, 75),
}


# --------------------------------------------------
# Useful functions
def calc_center_of_mass(cnt):
	M = cv2.moments(cnt)
	cx = int(M['m10'] / M['m00'])
	cy = int(M['m01'] / M['m00'])

	return (cx, cy)


def calc_dist(pos1, pos2):
	return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)

# --------------------------------------------------
# Class definition
# Single object information 
class SingleObjectInfo:
	def __init__(self, ID):
		self.ID = ID
		self.prev_contour = None
		self.prev_min_rect = None
		self.prev_cnt_area = None
		self.position_list = deque(maxlen=conf.NUM_FRAMES_TO_TRACK_PATH)
		self.last_actual_update = 0 # How many frames are expired after actual detection
		self.num_actual_updates = 0

	def update_movement(self, cnt, is_actual):
		# store contour and update position (based on center of mass)
		self.prev_contour = cnt
		self.prev_min_rect = cv2.minAreaRect(cnt)
		self.prev_cnt_area = cv2.contourArea(cnt)
		self.position_list.append(calc_center_of_mass(cnt))

		if is_actual:
			self.last_actual_update = 0
			self.num_actual_updates += 1

	def __repr__(self):
		return "'" + self.ID + " -> " + str(self.last_actual_update) + "'"

# Object tracking main class
class TEObjectTracker:
	def __init__(self):
		# background subtraction backend
		self.bs = bs_selector[conf.BG_SUBTRACTOR]()

		# Post processing configuration
		self.noise_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, conf.FILTER_NOISE_SIZE)

		# TODO: Object tracking data structure (list of SingleObjectInfo)
		self.total_seen_objects = 0
		self.tracked_objects = []

		# blank image (to be used for contours)
		self.blank = None
		
	# Main member function for updating with a new frame
	def feed_frame(self, frame):
		# 0. Initialize data structures (only once)
		if self.blank is None:
			self.blank = np.zeros(frame.shape[0:2])

		# 1. Background subtraction
		fgmask = self.bs.apply(frame)
		fgmask_post = fgmask.copy()

		# 2. Post processing
		# 2a. shadow handling (optional)
		if conf.NEGLECT_SHADOW:
			fgmask_post = cv2.threshold(fgmask_post, self.bs.getShadowValue() + 1, 255, cv2.THRESH_BINARY)[1] 

		# 2b. Remove noise (small sparse pixels)
		fgmask_post = cv2.morphologyEx(fgmask_post, cv2.MORPH_OPEN, self.noise_kernel)

		# 2c. Fill gaps
		fgmask_post = blur_selector[conf.GAP_FILLING_METHOD](fgmask_post)

		# 3. Object detection
		contours = cv2.findContours(fgmask_post.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
		contours = filter(lambda cnt:
				cnt is not None and
				len(cnt) > 0 and
				cv2.contourArea(cnt) > conf.MIN_OBJECT_AREA, contours)

		# 4. Track objects
		self.track_objects_from_contours(contours)

		return contours, fgmask, fgmask_post

	def get_tracked_objects(self, only_now_seen_objects = False):
		confirmed_objects = filter(
				lambda sobj: sobj.num_actual_updates > conf.NUM_FRAMES_TO_CONFIRM_OBJECTS,
				self.tracked_objects)

		if only_now_seen_objects:
			return filter(lambda sobj: sobj.last_actual_update == 0, confirmed_objects)

		return confirmed_objects

	# return if the two countours intersect each other
	def check_intersection_from_contours(self, cnt1, cnt2):
		img1 = cv2.drawContours(self.blank.copy(), [cnt1], -1, 1)
		img2 = cv2.drawContours(self.blank.copy(), [cnt2], -1, 1)

		intersection = np.logical_and(img1, img2)
		return np.count_nonzero(intersection) > 0

	# return if the two countours intersect each other using rotated rect
	# (slight inaccurate but much faster)
	def check_intersection_from_rect(self, rect1, rect2):
		ret, _ = cv2.rotatedRectangleIntersection(rect1, rect2)
		return ret != cv2.INTERSECT_NONE

	# return if the two countour sizes are similar
	def check_area_size_similarity(self, area1, area2):
		return abs(1 - (area1 / area2)) < conf.MAX_RATIO_OF_AREA_CHANGE

	# Sub function to track by identifying same objects (mainly private use)
	def track_objects_from_contours(self, contours):
		# 1. Update the number of frames from the last actual update
		for sobj in self.tracked_objects:
			sobj.last_actual_update += 1


		# 2. Update movement for each object (with adding new objects)
		for new_cnt in contours:
			pos = calc_center_of_mass(new_cnt)
			rect = cv2.minAreaRect(new_cnt)
			area = cv2.contourArea(new_cnt)

			# Get the list of objects intersected with distance
			inter_objects = []
			for sobj in self.tracked_objects:
				#if self.check_intersection_from_contours(new_cnt, sobj.prev_contour):
				if self.check_intersection_from_rect(rect, sobj.prev_min_rect) and \
					self.check_area_size_similarity(area, sobj.prev_cnt_area):
					dist = calc_dist(pos, sobj.position_list[-1])
					inter_objects.append((sobj, dist))

			# Find closest points
			if len(inter_objects) > 0:
				min_sobj = min(inter_objects, key=operator.itemgetter(1))[0]
				min_sobj.update_movement(new_cnt, True)
			else:
				# No intersected object. Regard as a new object
				new_sobj = SingleObjectInfo("ID" + str(self.total_seen_objects))
				new_sobj.update_movement(new_cnt, True)
				self.tracked_objects.append(new_sobj)
				self.total_seen_objects += 1

		# 3. Remove old objects
		self.tracked_objects = filter(
				lambda sobj: sobj.last_actual_update < conf.NUM_FRAMES_TO_REMOVE_OBJECTS,
				self.tracked_objects)

		# 4. Update not-found object position
		for sobj in self.tracked_objects:
			if sobj.last_actual_update == 0:
				continue

			# Just assume that it's not moving
			# TODO: predict new position based on kalman filter
			sobj.update_movement(sobj.prev_contour, False)

	# Delete all tracked objects to newly start
	def flush_objects(self):
		self.tracked_objects = []
		self.total_seen_objects = 0
