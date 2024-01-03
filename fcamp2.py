from connectdb import *


class Camp:

    def __init__(self, 
                 campID : int
                , hpID : int
                , campname : str
                , campLocation : str
                , capacity : int
                , indoor : int
                , food_o : int
                , food_o_gf : int
                , food_o_nn : int
                , food_o_gf_nn : int
                , food_v : int
                , food_v_gf : int
                , food_v_nn : int
                , food_v_gf_nn : int
                , food_vg : int
                , food_vg_gf : int
                , food_vg_nn : int
                , food_vg_gf_nn : int
                , painRelief : int
                , bandages : int
                , sanitaryProducts : int):
        # CampID should be autogenerated?  To avoid camps getting the same ID
        # And hpID should come from somewhere else too.         
        self.campname = campname
        self.campLocation = campLocation
        self.capacity = capacity
        self.indoor = indoor
        self.food_o = food_o
        self.food_o_gf = food_o_gf
        self.food_o_nn = food_o_nn
        self.food_o_gf_nn = food_o_gf_nn
        self.food_v = food_v
        self.food_v_gf = food_v_gf
        self.food_v_nn = food_v_nn
        self.food_v_gf_nn = food_v_gf_nn
        self.food_vg = food_vg
        self.food_vg_gf = food_vg_gf
        self.food_vg_nn = food_vg_nn
        self.food_vg_gf_nn = food_vg_gf_nn
        self.painRelief = painRelief
        self.bandages = bandages
        self.sanitaryProducts = sanitaryProducts
        

    def add_camp_to_DB(self):
        with setup_conn() as conn:
            # TODO: if the camp already exists, then delete it before we insert it again.
            cursor = conn.cursor()
            data = (self.campname, self.campLocation, self.capacity, self.indoor
                    , self.food_o, self.food_o_gf, self.food_o_nn, self.food_o_gf_nn, self.food_v, self.food_v_gf, self.food_v_nn
                    , self.food_v_gf_nn, self.food_vg, self.food_vg_gf, self.food_vg_nn, self.food_vg_gf_nn
                    , self.painRelief, self.bandages, self.sanitaryProducts)
            insert_query(cursor, 'campsv2', data)
            conn.commit()

    def del_camp_from_DB(self):
        with setup_conn as conn:
            cursor = conn.cursor()
            delete_query(cursor, 'campsv2', )
#%%

import pandas as pd
import numpy as np

#%%


def get_camp_data():
    with setup_conn() as conn:
        cursor = conn.cursor()
        ## Get refugee data
        cursor.execute('SELECT * FROM refugee')
        r_colList=['refugeeID', 'name', 'surname', 'campID', 'languages', 'gender', 'age', 
                 'psyHealth', 'physHealth', 'familyID', 
                 'diet', 'glutenFree', 'noNuts', 
                 'epipen', 'painRelief', 'bandages', 'sanitaryProducts']
        df_refugee = pd.DataFrame()
        for row in cursor.fetchall():
            df_refugee = pd.concat([df_refugee, pd.DataFrame([row], columns = r_colList)])   
        ## Get camp data
        cursor.execute('SELECT * FROM camps')
        c_colList = ['campID', 'planID', 'campname', 'campLocation', 'capacity', 'indoor'
                   , 'food_om_na', 'food_om_gf','food_om_nn', 'food_om_gfnn'
                   , 'food_vt_na', 'food_vt_gf', 'food_vt_nn', 'food_vt_gfnn'
                   , 'food_vg_na', 'food_vg_gf', 'food_vg_nn', 'food_vg_gfnn'
                   , 'epipen', 'painRelief', 'bandages', 'sanitaryProducts']
        df_camp = pd.DataFrame()
        for row in cursor.fetchall():
            df_camp = pd.concat([df_camp, pd.DataFrame([row], columns = c_colList)])
        return (df_refugee, df_camp)
        
        
def calculate_camp_resource_status(sel_campID = 0):
    # Extract data from the database
    df_refugee, df_camp = get_camp_data()
    
    # Allergies list
    allergies = ['na', 'gf', 'nn', 'gfnn']
    
    ## Take copy of the dataframes
    df0 = df_refugee.copy()
    
    ## People
    needs_people = df0['campID'].value_counts().rename_axis('campID').reset_index(name = "count")
    needs_people['category'] = "beds"
    
    ## Unaccompanied minors
    df0['adults'] = np.where(df0['age']>=18, 1, 0)
    df0['minors'] = np.where(df0['age']< 18, 1, 0)
    ## Aggregate to family level
    tmpdf = df0[['campID', 'familyID', 'adults', 'minors']].groupby(['campID', 'familyID']).sum().reset_index()
    needs_guardians = tmpdf[tmpdf['adults']==0]['campID'].value_counts().rename_axis('campID').reset_index(name = 'count')
    needs_guardians['category'] = "guardians"
    
    ## Food
    ## First create a category variable to sum up by (rather than diet + allergies)
    df0['food_allergy'] = ('food_' + df0['diet'] + '_' + np.where((df0['glutenFree']==1) & (df0['noNuts']==1), "gfnn"
                        , np.where(df0['glutenFree']==1, "gf"
                        , np.where(df0['noNuts']==1, "nn", "na")))).str.lower()
    needs_food = df0[['campID', 'food_allergy']].value_counts().reset_index(name = "count").rename(columns={'food_allergy':'category'})
    
    ## Medical
    needs_medical = pd.concat([
                    df0[df0['epipen']==1]['campID'].value_counts().rename_axis('campID').reset_index(name = "count")
                  , df0[df0['painRelief']==1]['campID'].value_counts().rename_axis('campID').reset_index(name = "count")
                  , df0[df0['bandages']==1]['campID'].value_counts().rename_axis('campID').reset_index(name = "count")
                  , df0[df0['sanitaryProducts']==1]['campID'].value_counts().rename_axis('campID').reset_index(name = "count")
                  ], keys=["epipen", "painRelief", "bandages", "sanitaryProducts"]
        ).reset_index(names=['category', 'order'])
    needs_medical.drop(['order'], axis=1, inplace=True)
    
    # Combine all needs
    needs_all = pd.concat([needs_people, needs_food, needs_medical])
    
    # Now get camp data
    df1 = df_camp.copy()
    df1.drop(['planID', 'campname', 'campLocation', 'indoor'], axis=1, inplace=True)
    df1 = df1.rename(columns={"capacity":"beds"})
    invent_all = pd.melt(df1, id_vars=['campID'], value_vars = ['beds'
                                                                , 'food_om_na', 'food_om_gf','food_om_nn', 'food_om_gfnn'
                                                                , 'food_vt_na', 'food_vt_gf', 'food_vt_nn', 'food_vt_gfnn'
                                                                , 'food_vg_na', 'food_vg_gf', 'food_vg_nn', 'food_vg_gfnn'
                                                                , 'epipen', 'painRelief', 'bandages', 'sanitaryProducts']
                                                                , value_name = "qty")
    invent_all = invent_all.rename(columns={'variable':'category'})
    
    # Merge the needs against the inventory
    camp_check = invent_all.merge(needs_all, on=['campID', 'category'], how='left')
    #camp_check['counts'] = camp_check['counts'].fillna(0)
    camp_check['count'] = camp_check['count'].fillna(0).astype(int)
    camp_check['qty_surplus'] = camp_check['qty'] - camp_check['count']
    camp_check['deficient'] = camp_check['qty_surplus'] < 0
    
    if sel_campID == 0:
        return camp_check
    else:
        return camp_check[camp_check['campID'] == sel_campID]
    
    
#%%
def calculate_camp_needs():
    with setup_conn() as conn:
        # Get refugee data
        with setup_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM refugeesv2")
            for row in cursor.fetchall():
                print(row)
            
        # Get camp data



def delete_camp_by_id():  # called to delete a specific camp AND when a hp is deleted
    camp_id = get_id_for_removal()
    with setup_conn() as conn:
        cursor = conn.cursor()
        remove_query2(cursor, 'campsv2', 'campID', camp_id)


def delete_camp_by_hp(hp_id):
    with setup_conn() as conn:
        cursor = conn.cursor()
        remove_query2(cursor, 'camps', 'planID', hp_id)


def transfer_or_delete_people():
    camp_id = get_id_for_removal()
    print("\nWould you like to transfer the refugees and volunteers to a differnt camp before deleting it? (Yes/No) ")
    print("1. Yes")
    print("2. No")
    answer = int(input("\nChoose an option: "))

    if answer == 1:
        new_camp = input("\nWhich camp ID would you like to transfer the refugees to? ")
        transfer_camp_r_v(camp_id, new_camp) # transfer before deleting
        with setup_conn() as conn:
            cursor = conn.cursor()
            remove_query2(cursor, 'camps', 'campID', camp_id)
        print("\nCamp has been successfully deleted and refugees and volunteers transfered.")
    
    elif answer == 2:
        with setup_conn() as conn:
            cursor = conn.cursor()
            remove_query2(cursor, 'camps', 'campID', camp_id)
        print("\nCamp has been successfully deleted.")


def create_camp_input_hp(hp_id):
    input_capacity = int(input("Enter camp capacity: "))
    input_status = input("Enter camp status: ")
    return Camp(hp_id, input_capacity, 0, 0, input_status, '', 0, 0, 0, 0, 0, 0, 0)

def create_camp_input():
    input_hp_id = int(input("Enter plan ID: "))
    input_capacity = int(input("Enter camp capacity: "))
    input_status = input("Enter camp status: ")
    return Camp(input_hp_id, input_capacity, 0, 0, input_status, '', 0, 0, 0, 0, 0, 0, 0)

### update
def update_total_count():
    # update refugee and volunteer count in the camps table
    camp_id = get_id_for_update() ### SESSION
    with setup_conn() as conn:
        cursor = conn.cursor()
        count_v_data = get_count(cursor, 'users', 'campID', camp_id)
        # count_r_data = get_count(cursor, 'refugees', 'campID', camp_id)
        update_by_column(cursor, 'camps', 'totalVolunteers', 'campID', camp_id, count_v_data)
        # update_by_column(cursor, 'camps', 'totalRefugees', camp_id, count_r_data)


def update_camp_status(new_status):
    camp_id = get_id_for_status()
    # print(camp_id, new_status)
    with setup_conn() as conn:
        cursor = conn.cursor()
        update_camp_status_f(cursor, camp_id, new_status)
        # update_by_column(cursor,'camps','status', camp_id, 'campID', new_status)


def get_id_for_removal():
    camp_id = int(input("\nEnter the ID of the camp to be removed: "))
    return camp_id


def get_id_for_status():
    camp_id = int(input("\nEnter the ID of the camp whose status you want to be updated: "))
    return camp_id


def get_id_for_update():
    camp_id = int(input("\nEnter the ID of the camp to be updated: "))
    return camp_id


# things to do:
# once the refugees and volunteers and resources are assigned, update the table
# eg. count query for number of refugees that were added to the camp, same with vs
# for resources the default should be 'enough' but everytime the resources table is updated,
# the camp table should be updated as well

# if needed to pull the last input id use plan_id = cursor.lastrowid

'''
error handling:
- cap the number of camps one can create within a hp - not sure
- make sure the number of refugees doesnt exceed the capacity
- confirming the hp - should exist (during creating a hp)
- when adding a new camp ensure it is added to an existing hp
- input types
- what happens here when hp closes
- finish resources state
- prompt the next thing that happens after a function about the camp is called
'''
