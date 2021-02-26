import pandas

# Read dataframe values, convert to list for database
ccc_df = pandas.read_excel(io = "Database.xlsx", sheet_name = "Records")
ccc_df_list = ccc_df.values.tolist()

# Keep a dictionary of the column titles/indices per entry
headers = list(ccc_df.columns)
ccc_index_dict = {headers[i]: i for i in range(len(headers))}

# Lists for the performer objects, the output list, and declined list
ccc_performers = []
ccc_outputs = [['Name: ', 'Teacher: ', 'Month: ', 'Timeslot: ', 'Attendance: ', 'Eligibility: ']]
ccc_declined = [['Name: ', 'Teacher: ', 'Requested Months: ', 'Requested Timeslot: ', 'Eligibility: ', 'Attendance: ', 'Comments: ']]

# Read in excepted schools to the "1 per school" limit
ccc_school_excepts_df = pandas.read_excel(io = "Database.xlsx", sheet_name = "School Exceptions")
ccc_school_excepts = ccc_school_excepts_df.values.tolist()

class MonthTime:
    """To keep track of timings and the amount of available slots each month."""
    TIME_LIMIT, months = 155, {}

    # Exception: 20 minute slots, anything >= 20 minutes can pretty much do RTP in the next slot
    max_times = {5: 3, 10: 3, 15: 3, 20: 3, 25: 2, 30: 1}

    def __init__(self, name):
        """Keep track of attributes, store month in list"""
        self.name = name
        self.time, self.times_available = MonthTime.TIME_LIMIT, dict(MonthTime.max_times)
        MonthTime.months[name] = self

    def available(month, req):
        """Check availability."""
        m = MonthTime.months[month]

        # Does the time fit in, and are there slots for that time available in the month
        return m.time >= req and m.times_available[req] > 0

    def mod(month, req):
        """Modify month given a slot being used."""
        m = MonthTime.months[month]

        # Decrease total time and slots available
        m.time -= req
        m.times_available[req] -= 1

class Performer:
    """A class for representing a performer and timeslot."""

    # Store timeslots as tuples - performers in one "range" of slots
    # are promoted to the next (ex: you could go 20 to 25 or 20 to 30)
    times = [range(5,10), range(10,15), range(15,20), range(20, 30), range(30,40)]

    # Who can perform, then what months available
    # eligible_months = ['January', 'February', 'March', 'April', 'May', 'June', 'None']
    ineligibility_code = "NS"
    planned_months = ['February', 'March', 'April', 'May', 'June']

    # Limits and exceptions
    SCHOOL_LIMIT, TIME_LIMIT = 1, 155
    school_dict = dict(ccc_school_excepts)
    
    # Tracking constraints
    schools_per_month = {m: {} for m in planned_months}
    for m in planned_months:
        MonthTime(m)
    
    def __init__(self, name, school, eligibility, month1, month2, req_time, attendance):
        """Initialize performer with the appropriate attributes.
        Includes keeping track of eligibility, timeslot, comments, etc. 
        """
        # Set attributes
        self.name, self.school, self.attendance = name, school, attendance
        self.month1, self.month2 = month1, month2
        self.req_time = req_time
        self.eligibility = eligibility
        self.comments = ""
 
    def assign(self):
        """Assigns slot if validated, else declines. Only for new performers."""
        m1, m2 = self.month1, self.month2 # months for easy reference
        msl, msa = self.month_school_limit, self.month_slot_available 

        # All reasons that this doesn't work, in order
        self.declined = True
       # if type(self.attendance) != int:
       #     self.comments = "Could not find attendance records"
        if self.eligibility == Performer.ineligibility_code:
            self.comments = "The performer's ability to perform in this half is uncertain"
        #elif not self.validate_time():
        #    self.comments = "Timeslot: " + str(self.req_time) + " minutes is not a permissible selection, given the last slot was " + str(self.last_time) + (" minutes" if not self.new else "") 
        elif not (msl(m1) or msl(m2)):
            self.comments = "For months " + m1 + " and " + m2 + ", the school limit for " + self.school + " is reached"
        elif not (msa(m1) or msa(m2)):
            self.comments = "For months " + m1 + " and " + m2 + ", the " + str(self.req_time) + "-minute slot is unavailable"
        else:
            # Success!
            self.declined = False
            self.set_month_and_time()
    
    def month_slot_available(self, month):
        """Checks whether month has the appropriate slot."""
        return MonthTime.available(month, self.req_time)
    
    def month_school_limit(self, month):
        """Checks whether the number of students in one school
        for a given month does not exceed limit.
        Note: Limit can be the standard, or non-standard if the school is in exceptions dictionary."""
        return Performer.schools_per_month[month].get(self.school, 0) < Performer.school_dict.get(self.school, Performer.SCHOOL_LIMIT)
    
    def set_month_and_time(self):
        """Modify the appropriate records for school and timeslot in the chosen month."""
        m1, m2 = self.month1, self.month2 # easy reference
        msa, msl = self.month_slot_available, self.month_school_limit # again, easy reference

        # Choose the working month and do the magic
        month = m1 if msl(m1) and msa(m1) else m2
        Performer.schools_per_month[month][self.school] = Performer.schools_per_month[month].get(self.school, 0) + 1
        MonthTime.mod(month, self.req_time)

        # Record final results
        self.this_month, self.this_time = month, self.req_time

# Create performers from list of data and do assignment
for p in ccc_df_list:
    if not pandas.isnull(p[0]):
        pname, pschool = p[ccc_index_dict['Name: ']], p[ccc_index_dict['Teacher: ']]
        pmonth1, pmonth2 = p[ccc_index_dict["First choice: "]], p[ccc_index_dict['Second choice: ']]
        preq_time = p[ccc_index_dict['Requested time: ']]
        pattendance = p[ccc_index_dict['Attendance: ']]
        peligibility = p[ccc_index_dict["Eligibility"]]

        pf = Performer(name = pname, school = pschool, month1 = pmonth1, month2 = pmonth2, req_time = preq_time, attendance = pattendance, eligibility = peligibility)
        ccc_performers.append(pf)

# Sort from most to least attendance
ccc_performers.sort(key = lambda p: p.attendance, reverse = True)

ccc_month_output = {}

for month in Performer.planned_months:
    ccc_month_output[month] = []

# Do assignment
for p in ccc_performers:
    p.assign()

    # Sort into declined and accepted, record into month tables
    if p.declined:
        ccc_declined.append([p.name, p.school, p.month1 + ", " + p.month2, p.req_time, p.eligibility, p.attendance, p.comments])
    else:
        output_lst = [p.name, p.school, p.this_month, p.this_time, p.attendance, p.eligibility]
        ccc_outputs.append(output_lst)
        ccc_month_output[p.this_month].append(output_lst[0:2] + output_lst[3:])

# Write to DataFrame
ccc_outputs_df = pandas.DataFrame(ccc_outputs[1:], columns = ccc_outputs[0])
ccc_declined_df = pandas.DataFrame(ccc_declined[1:], columns = ccc_declined[0])

# Set up Excel sheet and format
xlwriter = pandas.ExcelWriter('Output.xlsx', engine = 'xlsxwriter')
format = xlwriter.book.add_format({'text_wrap': True})

# Write to sheets and finish
ccc_outputs_df.to_excel(xlwriter, sheet_name = 'Outputs')
ccc_declined_df.to_excel(xlwriter, sheet_name = 'Declined')

# Columns for each month sheet
ccc_month_cols = ccc_outputs[0][0:2] + ccc_outputs[0][3:]

# Write to each month sheet and finish
for month in ccc_month_output:
    ccc_month_df = pandas.DataFrame(ccc_month_output[month], columns = ccc_month_cols)
    ccc_month_df.to_excel(xlwriter, sheet_name = month + " 2021")

xlwriter.save()