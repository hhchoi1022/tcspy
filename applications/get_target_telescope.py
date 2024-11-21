#%%
# Step 1: Define available filters for each telescope
telescopes = {
    #"7DT01": ["u", "g", "r", "i", "z", "m400", "m425", "Slot8", "m675"],
    "7DT02": ["g", "r", "i", "m450", "m475", "Slot6", "m700", "Slot8", "Slot9"],
    "7DT03": ["g", "r", "i", "m500", "m525", "m450", "m725", "Slot8", "Slot9"],
    "7DT04": ["g", "r", "i", "m650", "m800", "m825", "Slot7", "Slot8", "Slot9"],
    "7DT05": ["g", "r", "i", "m550", "m575", "m475", "m750", "Slot8", "Slot9"],
    "7DT06": ["g", "r", "i", "m600", "m625", "m500", "m775", "Slot8", "Slot9"],
    "7DT07": ["g", "r", "i", "m650", "m675", "m525", "Slot7", "Slot8", "Slot9"],
    "7DT08": ["g", "r", "i", "m700", "m725", "m550", "Slot7", "Slot8", "Slot9"],
    "7DT09": ["g", "r", "i", "m750", "m775", "m575", "Slot7", "Slot8", "Slot9"],
    "7DT10": ["g", "r", "i", "z", "m800", "m825", "m600", "Slot8", "m425w"],
    "7DT11": ["g", "r", "i", "m850", "m425", "m625", "m400", "Slot8", "Slot9"],
    "7DT12": ["g", "r", "i", "m850", "m875", "Slot6", "Slot7", "Slot8", "Slot9"]
}

# Step 2: Define target observation requirements
target_filters = ['m400',  'm450', 'm500', 'm550', 'm600', 'm650', 'm475']

# Step 3: Backtracking to find valid assignments
def find_telescopes_for_filters(telescopes, target_filters, assigned=None):
    if assigned is None:
        assigned = {}
    print(assigned)

    # If all filters have been assigned, return the assignment
    if len(assigned) == len(target_filters):
        return assigned

    current_filter = target_filters[len(assigned)]  # Get the next filter to assign

    for telescope, filters in telescopes.items():
        if telescope not in assigned.values() and current_filter in filters:  # Ensure the telescope isn't already assigned
            assigned[current_filter] = telescope  # Try this assignment

            # Recursively try to assign the remaining filters
            result = find_telescopes_for_filters(telescopes, target_filters, assigned)
            if result:  # If the assignment was successful, return the result
                return result

            # Backtrack if the assignment didn't work
            del assigned[current_filter]

    return None  # Return None if no valid assignment is found

# Step 4: Trigger the observation
assigned_telescopes = find_telescopes_for_filters(telescopes, target_filters)

if assigned_telescopes:
    print("Required telescopes for the target observation:")
    for filter_needed, telescope in assigned_telescopes.items():
        print(f"Filter {filter_needed}: {telescope}")
else:
    print("The observation cannot be triggered because no valid assignment of telescopes was found.")

# %%
