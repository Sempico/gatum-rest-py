# Python library for Gatum REST API

The library for interacting with [Gatum REST API](https://restapi.gatum.io/desc/).

Requires Python 3.10 or later.

## Getting Started

To use the library, first install it from PyPI using `pip`:

    pip install gatum-rest-py


## Usage for Gatum REST API

### Getting a REST API token
To get a REST API token, you need to go through the OAuth2.0 authorization procedure using your login and password from WEB account.
```py
from gatum_rest_py import GatumRESTAPI

# base_url should be replaced with the URL of your vendor
client = GatumRESTAPI(base_url='https://restapi.gatum.io/')
response = client.access_token(username='your_login', password='your_password')

print(f'HTTP Status code: {response.status_code}')
print(f'JSON data: {response.json()}')
```
The output:
```
HTTP Status code: 200
JSON data: {'status': True, 'data': {'access_token': 'gbBX8dB7kDvBeo0H-VN2CX0bAXXbyJ', 'expires_at': 2006432128}}
```
or
```
HTTP Status code: 400
JSON data: {'status': False, 'error_code': 400, 'errors': {'password': ['Incorrect username or password.']}}
```
### Account Information
```py
from gatum_rest_py import GatumRESTAPI

client = GatumRESTAPI(base_url='https://restapi.gatum.io/')
access_token = 'your_token'
response = client.account_info(access_token=access_token)
print(response.json()) # You will receive detailed information about your account in dictionary format
```
### Register a new customer
```py
from gatum_rest_py import GatumRESTAPI

client = GatumRESTAPI(base_url='https://restapi.gatum.io/')

response = client.register_customer(login='restap141i', # required, login of a new account
                                    password='restapirestapi', # required, password of a new account
                                    name='John', # required, name of the person responsible for the new account
                                    phone='1234567890', # required, contact phone number
                                    email='john.doe@gmail.com', # required
                                    company_name='John Doe LTD', # optional
                                    skype='johndoe') # optional
print(response.json())
```
### Send SMS
```py
from gatum_rest_py import GatumRESTAPI

client = GatumRESTAPI(base_url='https://restapi.gatum.io/')
access_token = "your_token"

response = client.send_sms(access_token=access_token, 
                           numbers=["380957225759", "380661093766"], # required, list of destination phone numbers in MSISDN format
                           sender_id="Verify", # required, numeric SID length must be 3-15 symbols, 
                                            # alphanumeric SID length must be <= 11 symbols
                           text="Your OTP is 42488", # required
                           sms_type="sms", # optional, allowed types: 'sms', 'hlr', 'mnp', by default: 'sms'
                           lifetime='86400',  # optional, how many seconds this SMS will live, by default: '86400'
                           begin_date='2023-03-19',  # optional, the date when SMS should be sent,
                                                     # format: 'YYYY-MM-DD', by default: the current date
                           begin_time='19:16:00', # optional, the time when SMS should be sent in GMT+0 in selected beginDate,
                                                  # format: 'HH:MM:SS', by default: the current time
                           delivery=True) # optional, whether to return the DLR, True or False, by default: True

print(response.json())
```
### Get info about sent SMS
```py
from gatum_rest_py import GatumRESTAPI

client = GatumRESTAPI(base_url='https://restapi.gatum.io/')
access_token = "your_token"

response = client.sms_full_data(access_token=access_token,
                                mcc=255, # optional, filter by MCC
                                mnc=0, # optional, filter by MNC
                                sender_id="Verify", # optional, filter by Sender ID
                                phone=["380957225759", "380661093766"], # optional, filter by phone numbers
                                id_base=[2, 4, 6, 22], # optional, filter by Group ID
                                limit=None, # optional, number of SMS about which to return data
                                time_period="2023-07-24 00:00:00 - 2023-07-24 23:59:59", # optional, filter by SMS sending period
                                type_sms='sms') # optional, filter by sms type, allowed types: 'sms', 'hlr', 'mnp'
print(response.json())

# All optional parameters can be omitted, such a function call will return data on all sms for the last few days:
response = client.sms_full_data(access_token=access_token)
print(response.json())
```
### Working with Group of numbers
#### View the list of Groups:
```py
from gatum_rest_py import GatumRESTAPI

client = GatumRESTAPI(base_url='https://restapi.gatum.io/')
access_token = "your_token"

# information about the first 10 groups will be obtained:
response = client.list_group(access_token=access_token, limit=10, offset=0) 
print(response.json())

# to get information about the next 10 groups, you need to change the offset parameter:
response = client.list_group(access_token=access_token, limit=10, offset=1)
print(response.json())

# also you can get information about a particular group by its ID:
response = client.list_group(access_token=access_token, id_group=957)
print(response.json())
```
#### Create a new Group:
```py
from gatum_rest_py import GatumRESTAPI

client = GatumRESTAPI(base_url='https://restapi.gatum.io/')
access_token = "your_token"

response = client.create_group(access_token=access_token, 
                               name_group='All clients', # required
                               time_birth='13:00', # optional, what time to send greetings
                               originator_birth='Greetings', # optional, sender ID with which the greeting will be sent
                               text_birth='Happy birthday, #first_name#!', # optional, greeting text, 
                                                                           # #first_name# will be replaced with the corresponding name from the database
                               on_birth=True) # whether to send a greeting
print(response.json())

# The parameters time_birth, originator_birth, text_birth, on_birth can be omitted if greetings are not needed. 
# They will be set to False by default:
response = client.create_group(access_token=access_token, name_group='Clients for Promo')
print(response.json())
```
#### Delete list of groups by IDs:
```py
from gatum_rest_py import GatumRESTAPI

client = GatumRESTAPI(base_url='https://restapi.gatum.io/')
access_token = "your_token"

response = client.delete_group(access_token=access_token, id_group=[957, 959])
print(response.json())
```
### Working with numbers in Group
#### Add phone numbers to a Group:
```py 
from gatum_rest_py import GatumRESTAPI

client = GatumRESTAPI(base_url='https://restapi.gatum.io/')
access_token = "your_token"

# The format of the list of numbers should be as follows.
# Only the number parameter is required, other parameters can be omitted:
numbers = [{'number': 12345678901, 
            'name': 'Iogan', 
            'surname': 'Bah', 
            'patronymic': 'Sebastian', 
            'date_birth': '1992-12-31', 
            'male': 'm', 
            'note_1': 'tralivali', 
            'note_2': 'tralivali2', 
            'note_3': 'tralivali3', 
            'note_4': 'tralivali4', 
            'note_5': 'tralivali5', 
            'note_6': 'tralivali6', 
            'note_7': 'tralivali7', 
            'note_8': 'tralivali8', 
            'note_9': 'tralivali9', 
            'note_10': 'tralivali10'}, 
           {'number': 12345678900, 
            'name': 'Liza', 
            'surname': 'Bah', 
            'patronymic': '', 
            'date_birth': '1992-12-31', 
            'male': 'f', 
            'note_1': 'tralivali', 
            'note_2': 'tralivali2', 
            'note_3': 'tralivali3', 
            'note_4': 'tralivali4', 
            'note_5': 'tralivali5', 
            'note_6': 'tralivali6', 
            'note_7': 'tralivali7', 
            'note_8': 'tralivali8', 
            'note_9': 'tralivali9', 
            'note_10': 'tralivali10'}]

response = client.group_number_add(access_token=access_token, 
                                   id_group=956, # required, Group ID to add numbers to
                                   numbers=numbers) # required
print(response.json())
```
#### Search for phone numbers in the Group:
```py 
from gatum_rest_py import GatumRESTAPI

client = GatumRESTAPI(base_url='https://restapi.gatum.io/')
access_token = "your_token"

response = client.group_number_search(access_token=access_token, 
                                      id_group=956, 
                                      numbers=[12345678900, 12345678901, 17133010164])
print(response.json())
```
#### Delete phone numbers from the Group:
```py 
from gatum_rest_py import GatumRESTAPI

client = GatumRESTAPI(base_url='https://restapi.gatum.io/')
access_token = "your_token"

response = client.group_number_delete(access_token=access_token, 
                                      id_group=956, 
                                      numbers=[12345678900, 12345678901, 17133010164])
print(response.json())
```
#### Make SMS sending to numbers from Groups:
The `id_group`, `id_group_excluded` and `phone` parameters are used to designate the numbers to which you want to send.<br>
If the `id_group_excluded` parameter is used, then all numbers contained in these groups will be excluded from the sending,  
despite the fact that they may be in the groups specified by the `id_group` parameter or in the list specified by the `phone` parameter. <br> 
The `id_group_excluded` and `phone` parameters can be omitted if they are not required.<br><br> 

The `date_start`, `time_start` and `time_stop` parameters are used to schedule SMS sending.<br>
If these parameters are set, then SMS will be sent gradually over the specified period of time.<br>
If you need to send SMS immediately, then these parameters can be omitted.<br>
```py 
from gatum_rest_py import GatumRESTAPI

client = GatumRESTAPI(base_url='https://restapi.gatum.io/')
access_token = "your_token"

response = client.send_bulk(access_token=access_token,
                            sender_id='VShop', # required
                            text='Place an order today and get a discount', # required
                            id_group=[956, 959], # required, list of number group IDs for sending
                            id_group_excluded=[957], # optional
                            phone=['1234567890', '1234567891'], # optional
                            date_start='2023-08-02', # optional
                            time_start='10:00', # optional
                            time_stop='17:00') # optional

print(response.json())
```
### Working with Personal Black List
#### Add a list of numbers to the Black List:
```py
from gatum_rest_py import GatumRESTAPI

client = GatumRESTAPI(base_url='https://restapi.gatum.io/')
access_token = "your_token"

response = client.black_list_add(access_token=access_token,
                                 numbers=[12345665777, 12345665772])

print(response.json())
```
#### Search the list of numbers in the Black list:
```py
from gatum_rest_py import GatumRESTAPI

client = GatumRESTAPI(base_url='https://restapi.gatum.io/')
access_token = "your_token"

response = client.black_list_search(access_token=access_token,
                                    numbers=[12345665777, 12345665772])

print(response.json())
```
#### Delete the list of numbers from the Black list:
```py
from gatum_rest_py import GatumRESTAPI

client = GatumRESTAPI(base_url='https://restapi.gatum.io/')
access_token = "your_token"

response = client.black_list_delete(access_token=access_token, 
                                    numbers=[12345665777, 12345665772])

print(response.json())
```

### Logout (token destroy)
```py
from gatum_rest_py import GatumRESTAPI

client = GatumRESTAPI(base_url='https://restapi.gatum.io/')
access_token = "your_token"

response = client.logout(access_token=access_token)
print(response.json())
```

### Receive DLR 
To receive DLR, you need to go to the `API` > `RESTAPI` section in your WEB cabinet and in the `DLR sending to webhook` field, specify the webhook URL where Gatum should send them.<br><br>
For example, you specified the URL of your webhook as `https://yourdomain.com/restdlr`, in this case, to send DLR Gatum will make a POST request to the URL `https://yourdomain.com/apidlr` with a JSON list of your DLRs data as payload. <br>
To confirm that you received the DLRs, you need to return a list of `id_state` parameter values in response to this request. <br><br>
An example of a simple listener written using the Python Flask framework:
```py
from flask import Flask, request

app = Flask(__name__)


@app.route('/restdlr', methods=['POST'])
def receive_dlr():
    rec_dlr = request.json
    id_list = []
    for item in rec_dlr:
        id_list.append(str(item['id_state']))

    print(f'DLRs data: {rec_dlr}')
    print(f'List of IDs: {id_list}')
    
    return id_list, 200


if __name__ == "__main__":
    app.run(debug=False, port=5000)
```
The output:
```
DLRs data: [{'id_state': 598933232, 'originator': 'SMS', 'phone': '380957225759', 'type_sms': 'sms', 'text_sms': 'Your OTP is 42432', 'num_parts': 1, 'part_no': 1, 'state': 'DELIVRD', 'time': '2023-07-24 12:03:48'}, {'id_state': 598933233, 'originator': 'SMS', 'phone': '380957225759', 'type_sms': 'sms', 'text_sms': 'Your OTP is 42432', 'num_parts': 1, 'part_no': 1, 'state': 'DELIVRD', 'time': '2023-07-24 12:03:48'}]
List of IDs: ['598933232', '598933233']
```


