import asyncio
import json
import requests
import pandas as pd

def retrieve_orders(cuid:str):
    """
    gets orders list for cuid
    
    Args:
        cuid (str): The cuid of the technician.
    
    Returns:
        orders (array): array of order details containing dictionaries
        
    """
    #print(f"Retrieving orders for cuid: {cuid}")
    api_url = "http://34.66.37.185:8085/getOrderDetails"
    params = {}
    if cuid:
        params['tech_cuid'] = cuid
    full_url = f"{api_url}?tech_cuid={cuid}"
    print(full_url)
 
    try:
        response = requests.get(full_url, params=params)
 
        if response.status_code == 200:
            # print("Response:", response.json())
            df=pd.DataFrame(response.json())
            df['DueDate']=pd.to_datetime(df['DueDate'])
            df.sort_values(by='DueDate')
            df = df.head(5)
            response = df.to_json(orient = 'records')
            

        else:
            print("Error:", response.status_code)
            print("Response:", response.text)
        #print(response)
        return {"success": True, "message": "order fetch successfull", "response": {"orders":response}}
    
    except Exception as e:
        print("An error occurred:", str(e))
        return e

def autodiscover_tool(Account_DTN:str, ethernet_port:str, fsan:str, model:str, cuid:str):
    """
    Runs the autodiscover for a for an ONT device.
    
    Args:
        Account_DTN (str): 10 digit telephone number in string format
        ethernet_port (str): 1 digit port number in string format
        fsan (str): " The serial number of the device
        model (str): The model number of the device.,
        cuid (str): The cuid of the technician.
    
    Returns:
        dict: Result of the autodiscover tool. and response json with necessary parameters
    """
    
    url = "http://34.66.37.185:8085/autodiscover"
    payload = {
        "dtn"          : Account_DTN,
        "ethernet_port": ethernet_port,
        "fsan"         : fsan,
        "model"        : model,
        "tech_cuid"    : cuid
    }
        
    headers = {
      'Content-Type': 'application/json'
    }
    log_type = 'autodiscover'
    
    print(f"Running autodiscover for serial number: {fsan}")
    # Simulate autodiscover process
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    result = response.json()
    transaction_id = result.get('transactionId')
    
    if not transaction_id:
        return {"success": False, "message": "Transaction ID not found in the response"}
 
    while True:
        result = show_live_logs(transaction_id, log_type)
        if result.get('IS_AUTO_DISCOVERED'):
            print('Auto discover is successful')
            return {"success": True, "message": "Auto discover is successful", "response": result}
 
        if not result.get('IS_AUTO_DISCOVERED'):
            message = result.get('MESSAGE')
            if message == 'Exception':
                print('Autodiscover failed. Check physical port')
                return {"success": False, "message": "Autodiscover failed. Check physical port", "response": None}
            elif message is None:
                print('Auto discover failed')
                return {"success": False, "message": "Autodiscover failed", "data": None}
            else:
                print(f'Auto discover failed with {message}')
                return {"success": False, "message": f"Auto discover failed with {message}", "response": None}
        
        # Sleep for 5 seconds before the next status check
        time.sleep(5)


def activation_tool(cuid : str,
                    OPTIC_LINE_TRMNL_OLT_CILLI : str,
                    PON_PORT_NUMBER : str,
                    LEG_NUMBER : str,
                    Account_DTN : str,
                    OLT_MAKE : str,
                    fsan : str,
                    TECHNOLOGY : str,
                    O2_SHELF_SLOT_PORT : str,
                    SHELF_SLOT_PORT : str,
                    ethernet_port : str,
                    model : str,
                    PRODUCT_SPEED : str,
                    CLAN : str,
                    VLAN : str,
                    TELNET_IP : str,
                    transaction_id : str):
    """
    Runs the activation tool with the provided input parameters.
    
    Args:
        cuid (str) : The cuid of the technician
        OPTIC_LINE_TRMNL_OLT_CILLI (str)  
        PON_PORT_NUMBER (str)  
        LEG_NUMBER (str)  
        Account_DTN (str)  
        OLT_MAKE (str)  
        fsan (str)  
        TECHNOLOGY (str)  
        O2_SHELF_SLOT_PORT (str)  
        SHELF_SLOT_PORT (str)  
        ethernet_port (str)  
        model (str)  
        PRODUCT_SPEED (str)  
        CLAN (str)  
        VLAN (str)  
        TELNET_IP (str)  
        transaction_id (str)  
    
    Returns:
        dict: Result of the activation tool.
    """
    
    url = "http://34.66.37.185:8085/activate"
 
    payload = {
        "tech_cuid"          : cuid,
        "olt_clli"           : OPTIC_LINE_TRMNL_OLT_CILLI,
        "ad_pon_port"        : PON_PORT_NUMBER,
        "o2_onu"             : LEG_NUMBER,
        "dtn"                : Account_DTN,
        "olt_vendor"         : OLT_MAKE,
        "ad_serialnumber"    : fsan,
        "inp_onu"            : LEG_NUMBER,
        "olt_technology"     : TECHNOLOGY,
        "o2_shelf_slot_port" : O2_SHELF_SLOT_PORT,
        "ad_shelf_slot_port" : SHELF_SLOT_PORT,
        "ethernet_port"      : ethernet_port, # from UI
        "olt_make_model"     : model,
        "product_speed"      : PRODUCT_SPEED,
        "cvlan"              : CLAN,
        "vlan"               : VLAN,
        "telnet_ip"          : TELNET_IP,
        "eth_undeploy_sts"   : False,
        "evc"                : None,
        "transaction_id"     : transaction_id
    }
    
    headers = {
      'Content-Type': 'application/json'
    }

    #print('payload: ',payload)
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        #transaction_id = result.get('transaction_id')  
        #print('payload: ',payload)
        #print('result: ',result)
        log_type = 'activation'
        while True:
            result = show_live_logs(transaction_id, log_type)
            status = result.get('status')
            #print(f"Activation result: {result}")

            if status == 'SUCCESS':
                print('Successful activation')
                return {"success": True, "message": "Successful activation", "response": result}

            elif status == 'FAILED':
                print('Activation failed')
                return {"success": False, "message": "Activation failed", "response": result}
            else:
                pass
            # Sleep for 5 seconds before the next status check
            time.sleep(5)
        
    except requests.RequestException as e:
        print(f'Error: {e}')
        return None




def show_live_logs(trasaction_id:str, log_type:str):

    print(f"Fetching status of: {log_type}")
    params = {"transaction_id": trasaction_id, "log_type": log_type}
    
    api_url = f"http://34.66.37.185:8085/showLiveLogs?transaction_id={trasaction_id}&log_type={log_type}"

    try:
        response = requests.get(api_url, params=params)
 
        response.raise_for_status()
        result = response.json()
        return result
            
    except requests.RequestException as e:
        print(f'Error: {e}')

    


def prioritize_order(orders:str):
    """
    Prioritizes output based on the due date and returns the order details
    
    Args:
        orders (str): this is array of orders in string format
        
    Returns:
        dict: prioritized order details
    """
    #print(orders)    
    parsed = json.loads(orders)
    result = parsed[0]
    return {"success": True, "message": "Activation failed", "response": {"prioritized_order": result}}