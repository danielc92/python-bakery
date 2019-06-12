#!/usr/bin/env python
# coding: utf-8

# # Task
# Given a customer order you are required to determine the cost and pack breakdown for each product.
# To save on shipping space each order should contain the minimal number of packs.

# # The Data
# Essentially the table of data is split into three concepts which can be abstracted out. I will be using `pandas` to manipulate and store the data. The concepts are;
# 
# - Products
# - Packs
# - Orders
# 
# I will not be modelling for Orders, as it would be overkill for this example.
# 
# The data should be denormalized and indexed in production in order to increase speed, storage efficiency and maintainability. Ideally, we would want to store this data in a relational database using a many to many relationship.

# In[1]:


import pandas


# ###  Create dataframes

# In[2]:


product_data = pandas.DataFrame({"product_row_id":[0, 1, 2],
                                 "product_name":["Vegemite Scroll", "Blueberry Muffin", "Croissant"], 
                                 "product_code":["VS5", "MB11", "CF"]})

packs_data = pandas.DataFrame({"pack_row_id": [0, 1, 2, 3, 4, 5, 6, 7],
                               "product_code":["VS5","VS5","MB11", "MB11", "MB11", "CF", "CF", "CF"],
                               "per_pack_quantity": [3, 5, 2, 5, 8, 3, 5, 9],
                               "pack_price": [6.99, 8.99, 9.95, 16.95, 24.95, 5.95, 9.95, 16.99]})


# ### Preview dataframes

# In[3]:


# print(product_data)


# In[4]:


# print(packs_data)


# In[5]:


normalized_data = pandas.merge(left=packs_data, right=product_data, on='product_code', how='left')


# In[6]:


# print(normalized_data)


# # Strategy
# For this particular problem I'm going to need:
# - Abstract the models from the data
#     - A product model
#     - A packs model
#     - A normalized (packs joined to product table)
# - Create a set of functions which form a pipeline. These functions will be;
#     1. `initial_clean()` - An initial clean of the input data
#     2. `get_pack_prices()` - Appends prices and bundles to input data
#     3. `get_pack_details()` - Appends pack details (divisions, remainders, pack size) recursively
#     4. `get_pack_subtotal()`- Calculates the input data subtotal
#     5. `get_packs_total()` - Calculates the total given an array of inputs
#     6. `pipeline()` - Combines all 5 functions above

# # Assumptions
# - Order units will be a positive integer
# - Remaining items cant be packed, order units would have to be incremented or decremented recursively to address this issue
# - Multiple Products can be placed in one order
# - Duplication of products within an order can occur
# - Pack tiers can be skipped (eg. 13 units of 'CF' should give 1x9pk and 1x3pk, skipping the 5pk)

# # Code
# Below I'll create the functions described in the **Strategy** section.

# In[7]:


def initial_clean(dictionary):
    
    """
    INPUT: A dictionary in the form {"product_code":"CF", "order_units": 50}
    OUTPUT: If the test passes, the same dictionary will be returned
    """
    
    # Store unique product codes
    unique_codes = normalized_data['product_code'].unique()
    
    # If product code does not exist or order units is not a positive number continue
    try: 
        if dictionary['product_code'] in unique_codes and dictionary['order_units'] > 0:
            return dictionary
    except Exception as e:
        print("Encountered an error {}".format(e))


# In[8]:


def get_pack_prices(dictionary, normalized_data):
    
    """
    INPUT: The output from initial_clean() function
    OUTPUT: The output from initial_clean() function appended with 
    pack_prices and per_pack_quantity key:value pairs
    """
    
    # Create a copy of normalized data given a product_code
    data = normalized_data[normalized_data['product_code'] == dictionary['product_code']]
    
    # Im only concerned with the per_pack_quantity and pack_price columns
    subset = data[['per_pack_quantity', 'pack_price']]
    
    # Sort the dataframe in pack_price descending
    subset_sorted = subset.sort_values('pack_price', ascending=False)
    
    # Store the pack prices and per pack quantities
    dictionary['pack_prices'] = list(subset_sorted['pack_price'])
    dictionary['per_pack_quantity'] = list(subset_sorted['per_pack_quantity'])
    
    return dictionary


# In[9]:


def get_pack_details(dictionary):
    
    """
    INPUT: The output from get_pack_prices
    OUTPUT: The output from get_pack_prices, appended with 'pack_details' key containing calculations
    made in order to derive the optimal number of divisions and remainders where 0 units are remaining
    """
    
    per_pack_quantity = dictionary['per_pack_quantity']
    
    # Set the initial index offset. To be incremented in each while loop
    n = 0
    
    # Onle execute until all pack quantities are exhausted
    while(n < len(per_pack_quantity)):
        
        # Reset pack level storage and per_pack_filtered before running through the for loop
        storage = []
        per_pack_filtered = per_pack_quantity[n:]
        
        # Run through per_pack_filtered, taking the index and item each iteration
        for index, item in enumerate(per_pack_filtered):
            
            # Conditionally calculate the divs and remainder based on the position of the index
            # It will need to be calculated differently if the index is 0 (start of array)
            if index == 0:
                divs = dictionary['order_units'] // item
                remainder = dictionary['order_units'] % item
            else:
                # Store the remaining orders by accessing the previous index value for 'remainder' in storage
                remaining_orders = storage[index - 1]['remainder']
                divs = remaining_orders // item
                remainder = remaining_orders % item
                
                # Initialize next_index, it it exist check ahead one item
                # This step is crucial for 'skipping' pack tiers as described in Assumptions section
                next_index = index + 1
                
                # Check if the next_index exists in the pack array
                if next_index < len(per_pack_filtered):
                    
                    # If it exists, check if the next index item is greater than the current remainder
                    # and the remainder is also greater than 0.
                    if per_pack_filtered[next_index] > remainder and remainder > 0:
                        divs = 0
                        remainder = remaining_orders
            
            # Store the calculated diviions, remainder, pack_size and absolute index
            # so that later on the subtotals can be calculated
            storage.append({'divisions':divs, 'remainder':remainder, 'pack_size': item, 'index': index + n})    
        
        # Store the remaining units
        remainder = storage[-1]['remainder']
        
        # If the remaining units is 0, we have reached optimal point, return the dictionary and exit function
        # If not, reset the while loop and start again from the next index of per_pack_quantities
        if remainder == 0:
            dictionary['pack_details'] = storage
            return dictionary
        
        n +=1


# In[10]:


def get_pack_subtotal(dictionary):
    
    """
    INPUT: The output of get_pack_details()
    OUTPUT:  The output of get_pack_details(), plus the pack level total price
    """
    
    dictionary['pack_total'] = 0
    prices = dictionary['pack_prices']
    
    for index, detail in enumerate(dictionary['pack_details']):
        price_index = detail['index']
        dictionary['pack_total'] += detail['divisions'] * prices[price_index]
    
    return dictionary


# In[11]:


def get_packs_total(orders):
    
    """
    INPUT: An array of outputs from get_pack_subtotal()
    OUTPUT: The total price of a variable number of inputs
    """
    
    total = sum([d['pack_total'] for d in orders])
    
    return total


# In[12]:


def pipeline(raw_orders):
    
    """
    INPUT: A dictionary in the form {"product_code":"CF", "order_units": 50}
    OUTPUT: If the test passes, the same dictionary will be returned
    """
    
    stage1_data = [initial_clean(order) for order in raw_orders if initial_clean(order) is not None]
    
    stage2_data = [get_pack_prices(order, normalized_data) for order in stage1_data]

    stage3_data = [get_pack_details(order) for order in stage2_data]

    stage4_data = [get_pack_subtotal(order) for order in stage3_data]

    total = get_packs_total(stage4_data)
    
    return total


# # Tests

# ### Test for 10 units of VS5

# In[13]:


# orders = [{'product_code':'VS5', 'order_units':10}]

# total = pipeline(raw_orders = orders)

# print(round(total,2))


# ### Test for 14 units of MB11

# In[14]:


# orders = [{'product_code':'MB11', 'order_units':14}]

# total = pipeline(raw_orders = orders)

# print(round(total, 2))


# ### Test for 13 units of CF

# In[15]:


# orders = [{'product_code':'CF', 'order_units':13}]

# total = pipeline(raw_orders = orders)

# print(round(total, 2))


# ### Test for multiple orders

# In[16]:


# orders = [{'product_code':'CF', 'order_units': 13}, 
#           {'product_code':'MB11', 'order_units': 14},
#           {'product_code':'VS5', 'order_units': 20}]

# total = pipeline(raw_orders = orders)

# print(round(total, 2))


# # Scaling/Production
# - In an ideal situation this code could be encapsulated within a web application using a framework such as Django.
# - In production recursive calls (**get_pack_details()**) would be very expensive, you could implement a caching mechanism with Redis or Memcached to alleviate load on the CPU dramatically.
# - The models can be created easily and mapped to a database of choice.
# - The orders can be cached and confirmed before they are committed to the database
# - The code itself is highly scalable as it accounts for an unlimited number of inputs
# - The code is also dynamic in that it can query a database / data structure. i.e. the code will work if we added new items to the database.


"""
RUN SCRIPT
"""

if __name__ == '__main__':


    # Validate and store code
    while(True):
        try:
            code_input = input('Enter a product code:')
            code_input = str(code_input).upper().strip()
            break
        except:
            print('Try again, input must be a string representing a product code')


    # Validate and store quantity
    while(True):
        try:
            quantity_input = input('Enter a order quantity:')
            quantity_input = int(quantity_input)
            if quantity_input > 0:
                break
            else:
                print('Try again, input must be positive integer')
        except:
            print('Try again, input must be positive integer')


    # Calculate total, with validated inputs

    total = pipeline([{'product_code': code_input,
                       'order_units': quantity_input}])

    # Print total
    print('The total is {0:.2f}'.format(total))
