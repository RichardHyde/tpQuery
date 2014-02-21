#!/usr/bin/python
from datetime import datetime
import glob, os, re, sys

padChar = "  "
lf = os.linesep

#============= Class Definitions ===============
class TaskBase:
	def __init__(self, text="", parent=None):
		self.text = text
		self.parent = parent
		self.subTasks = []
		self.complete = None
		self.completeDate = None
		self.note = ""
		self.tags = []

		if (parent is not None):
			parent.add(self)


	def __str__(self):
		return self.text

	def add(self, subTask):
		self.subTasks.append(subTask)
		subTask.parent = self

	def Complete(self):
		completeDate = datetime.min
		if (len(self.subTasks) > 0 and not self.complete):
			for t in self.subTasks:
				if (not t.Complete()):
					return False
				else:
					if (completeDate < t.completeDate):
						completeDate = t.completeDate

			self.complete = True
			self.completeDate = completeDate
			return True
		else:
			return self.complete

	def Print(self):
		print self.text

	def depth(self):
		if (self.parent != None):
			return self.parent.depth()+1
		else:
			return 0

	def parentTitles(self):
		result = ""

		if (self.parent != None):
			result = self.parent.parentTitles()

		result = result + self.text + " : "

		return result

class Task(TaskBase):
	def __init__(self, text="", parent=None):
		TaskBase.__init__(self, text, parent)
		self.complete = False
		self.completeDate = None

	def __str__(self):
		result = ""
		tags = ""

		if (self.tags):
			tags = " " + " ".join(self.tags).rstrip()

		result = padChar*self.depth() + "- " + self.text + tags

		if (self.Complete()):
			result = result + " @done(" + self.completeDate.strftime("%Y-%m-%d %H:%M:%S") + ")"

		if (len(self.note) > 0):
			result = result + lf + padChar*(self.depth() + 1) + self.note

		return result

	def Print(self):
		print "" + self.__str__()

		for t in self.subTasks:
			print "" + t.__str__()

class Project(TaskBase):
	def __init__(self, text="", parent=None):
		TaskBase.__init__(self, text, parent)

	def __str__(self):
		return padChar*self.depth() + self.text + ":"

	def Print(self):
		print "" + self.__str__()

		for p in self.subTasks:
			print "" + p.__str__()

#============= Functions ===============
## Get the home folder
def getHome():
	home = ""

	# Look for the linux home environment variable
	try:
		home = os.environ["HOME"]
	except:
		pass

	if (home == ""):
		# Look for the windows USERPROFILE environment variable
		try:
			home = os.environ["USERPROFILE"]
		except:
			pass

	# couldn't get the users home directory
	if (home == ""):
		print "can't locate home directory"
		sys.exit(-1)

	return home

## Display the usage for the program
def usage():
	print '''Usage:

tpQuery.py -f <filename> <query>

-s, --file : name of the file to query
		'''
	sys.exit(-2)

## Extract the passed in options
def getOpts(argv):
	fileName = "*.taskpaper"
	query = ""

	# print usage and exit if no options passed in
	if len(argv) == 0:
		usage()

	argc = 0

	while (argc < len(argv)):
		if (argv[argc] in ("-f", "--file")):
			fileName = argv[argc+1]
			argc = argc + 1
		else:
			query = query + " " + argv[argc]
		argc = argc + 1

	return fileName, query.strip(" ")

## Load a file in
def loadFile(fileName):
	f=open(fileName)
	nt = None
	p = None
	t = []

	for line in f:
		line = line.rstrip("\t \r\n")

		if (len(line) == 0):
			continue

		(depth, line) = lineDepth(line)

		if (line.endswith(':')):
			line = line.rstrip(':')
			nt = Project(line)
		elif (line.startswith("- ")):
			line = line.lstrip("- ")
			nt = Task(line)

			tags = re.findall(r"(@[\w\(\)\-]+)", line, re.S)

			if (tags):
				nt.tags = tags
				for tag in tags:
					nt.text = nt.text.replace(tag, "").rstrip()

		else:
			nt = None

		if (nt != None):
			if (depth == 0 or p == None):
				t.append(nt)
			else:
				while (p.depth() >= depth):
					p = p.parent
				p.add(nt)
			
			p = nt
		else:
			if (p != None and (p.depth()+1 == depth)):
				p.note = p.note + line + lf

	f.close()

	return t

## Calculate the depth of a line
def lineDepth(line):
	depth = 0

	while(line.startswith("  ") or line.startswith('\t')):
		depth = depth + 1
		if line.startswith("  "):
			line = line[2:]
		else:
			line = line[1:]

	return depth, line


## Check each task against the query
def findMatches(task, query):
	matches = []

	if (testQuery(task, query)):
		matches.append(task)

	for t in task.subTasks:
		matches = matches + findMatches(t, query)

	return matches

def testQuery(task, query):
	result = False
	bNot = False
	bOr = False
	bFirst = True
	bInBracket = False
	bracketedBit = ""

	for q in query.split(" "):
		if (bInBracket):
			if (q.count(')') > q.count('(')):
				bInBracket = False
				q = q[:-1]

			bracketedBit = bracketedBit + " " + q

			if (not bInBracket):
				r = testQuery(task, bracketedBit)

				if (bNot):
					r = not r

				if (bOr):
					result = result or r
				else:
					result = (result or bFirst) and r

				# Reset flags
				bNot = False
				bOr = False
				bFirst = False
				bracketedBit = ""
		else:
			if (q == "not"):
				bNot = True
			elif (q == "or"):
				bOr = True
			elif (q == "and"):
				bOr = False
			elif (q.startswith('(')):
				bracketedBit = q[1:]
				bInBracket = True
			else:
				r = False
				if (q.startswith("@")):
					if ("(" in q and ")" in q):
						qTag = q[:q.index("(")]
						qDate = q[q.index("(")+1:-1]
						qCheck = ""

						while (qDate[0] in ["<", ">", "="]):
							qCheck = qCheck + qDate[0]
							qDate = qDate[1:]

						if (qDate == ""):
							continue
							
						qDate = datetime.strptime(qDate, '%Y-%m-%d')

						for t in task.tags:
							if (t.startswith(qTag+"(")):
								tDate = datetime.strptime(t[len(qTag)+1:-1], '%Y-%m-%d')

								if (qCheck == "<"):
									r = (tDate < qDate)
								elif (qCheck == "<="):
									r = (tDate <= qDate)
								elif (qCheck == ">"):
									r = (tDate > qDate)
								elif (qCheck == ">="):
									r = (tDate >= qDate)
								elif (qCheck == "!"):
									r = not (tDate == qDate)
								else:
									r = (tDate == qDate)
								
								break
					else:
						for tag in task.tags:
							if (("(" in tag and ")" in tag and tag[:tag.index("(")] == q) or q == tag):
								r = True
								break
				else:
					r = (q in task.text or q in task.note)

				if (bNot):
					r = not r

				if (bOr):
					result = result or r
				else:
					result = (result or bFirst) and r

				# Reset flags
				bNot = False
				bOr = False
				bFirst = False

	return result

#=========== MAIN ===================
def main(argv):
	matches = []
	(fileName, query) = getOpts(argv)

	if (fileName+query == ""):
		usage()

	for fn in glob.glob(fileName):
		tasks = loadFile(fn)

		for t in tasks:
			matches = matches + findMatches(t, query)

	projectTitle = ""
	for t in matches:
		if (t.parent != None and projectTitle != t.parent.parentTitles):
			if (t.parent != None):
				projectTitle = t.parent.parentTitles()
			print projectTitle

		print t

		for t2 in t.subTasks:
			print t2

#========== Entry Point =============
if __name__ == "__main__":
	main(sys.argv[1:])
