import requests


class GatumRESTAPI:

    def __init__(self, base_url):
        self.__username = ''
        self.__password = ''
        self.__headers = {
            "Content-Type": "application/json"
        }
        # REST API URLs
        # OAuth2.0 auth token:
        self.__authorize_path = base_url + '/v1/authorize'
        self.__accesstoken_path = base_url + '/v1/accesstoken'
        # About me:
        self.__me_path = base_url + '/v1/me'
        # Register a customer:
        self.__register_path = base_url + '/v1/register'
        # Send SMS:
        self.__send_sms_path = base_url + '/v1/send'
        # Get info about sent SMS:
        self.__sms_full_data_path = base_url + '/v1/sms-full-data'
        # Working with group of numbers:
        self.__list_group_path = base_url + '/v1/group'
        self.__group_create_path = base_url + '/v1/group-create'
        self.__group_delete_path = base_url + '/v1/group-delete'
        # Working with numbers in Group:
        self.__group_num_add_path = base_url + '/v1/group-number-add'
        self.__group_num_search_path = base_url + '/v1/group-number-search'
        self.__group_num_del_path = base_url + '/v1/group-number-delete'
        self.__send_bulk_path = base_url + '/v1/send-bulk'
        # Working with personal Black list:
        self.__blacklist_add_path = base_url + '/v1/black-list-add'
        self.__blacklist_search_path = base_url + '/v1/black-list-search'
        self.__blacklist_del_path = base_url + '/v1/black-list-delete'
        # Refactoring SMS credentials:
        self.__replacement_path = base_url + '/v1/replacement'
        # Logout (token destroy):
        self.__logout_path = base_url + '/v1/logout'
        # Additional REST APIs:
        self.__product_price_path = base_url + '/v1/product-price'
        self.__account_price_path = base_url + '/v1/account-price'
        self.__country_price_path = base_url + '/v1/country-price'
        self.__country_by_continent_path = base_url + '/v1/country-by-continent'

    # OAuth2.0 auth token:
    def access_token(self, username='', password=''):
        self.__username = username
        self.__password = password
        response = self._authorize()
        if response.status_code == 200:
            payload = {"authorization_code": response.json()['data']['authorization_code']}
            response = self._make_post_request(self.__accesstoken_path, headers=self.__headers, payload=payload)
            return response
        else:
            return response

    def _authorize(self):
        payload = {'username': self.__username,
                   'password': self.__password,
                   }
        response = self._make_post_request(self.__authorize_path, headers=self.__headers, payload=payload)
        return response

    # About me:
    def account_info(self, access_token):
        headers = {'X-Access-Token': access_token}
        response = self._make_get_request(self.__me_path, headers=headers)
        return response

    # Register a customer:
    def register_customer(self, login, password, name, phone, email, company_name=None, skype=None):
        payload = {'login': login,
                   'password': password,
                   'name': name,
                   'phone': phone,
                   'email': email}
        if company_name is not None:
            payload.update({'company_name': company_name})
        if skype is not None:
            payload.update({'skype': skype})

        response = self._make_post_request(self.__register_path, headers=self.__headers, payload=payload)
        return response

    # Send SMS:
    def send_sms(self, access_token, numbers, sender_id, text, sms_type='sms',
                 begin_date=None, begin_time=None, lifetime=None, delivery=True):
        headers = {'X-Access-Token': access_token, 'charset': 'UTF-8'}
        headers.update(self.__headers)
        payload = [{
            'number': numbers,
            'senderID': sender_id,
            'text': text,
            'type': sms_type,
            'delivery': delivery
        }]
        if lifetime is not None:
            payload[0].update({'lifetime': lifetime})
        if begin_date is not None:
            payload[0].update({'beginDate': begin_date})
        if begin_time is not None:
            payload[0].update({'beginTime': begin_time})

        response = self._make_post_request(self.__send_sms_path, headers=headers, payload=payload)
        return response

    # Get info about sent SMS:
    def sms_full_data(self, access_token, mcc=None, mnc=None, sender_id=None, phone=None,
                      id_base=None, time_period=None, type_sms=None, limit=None):
        headers = {'X-Access-Token': access_token}
        headers.update(self.__headers)
        payload = {}
        if mcc is not None:
            payload.update({'MCC': mcc})
        if mnc is not None:
            payload.update({'MNC': mnc})
        if sender_id is not None:
            payload.update({'sender': sender_id})
        if phone is not None:
            payload.update({'phone': phone})
        if id_base is not None:
            payload.update({'id_base': id_base})
        if time_period is not None:
            payload.update({'time_period': time_period})
        if type_sms is not None:
            payload.update({'type_sms': type_sms})
        if limit is not None:
            payload.update({'limit': limit})

        response = self._make_post_request(self.__sms_full_data_path, headers=headers, payload=payload)
        return response

    # Working with group of numbers:
    def list_group(self, access_token, id_group=None, limit=10, offset=0):
        headers = {'X-Access-Token': access_token}
        headers.update(self.__headers)
        payload = {
            'limit': limit,
            'offset': offset
        }
        if id_group is not None:
            payload.update({'id_group': id_group})

        response = self._make_post_request(self.__list_group_path, headers=headers, payload=payload)
        return response

    def create_group(self, access_token, name_group, time_birth=False, originator_birth=False, text_birth=False,
                     on_birth=False):
        headers = {'X-Access-Token': access_token}
        headers.update(self.__headers)
        payload = {
            'name_group': name_group,
            'time_birth': time_birth,
            'originator_birth': originator_birth,
            'text_birth': text_birth,
            'on_birth': on_birth
        }
        response = self._make_post_request(self.__group_create_path, headers=headers, payload=payload)
        return response

    def delete_group(self, access_token, id_group):
        headers = {'X-Access-Token': access_token}
        headers.update(self.__headers)
        payload = {
            'id_group': id_group
        }
        response = self._make_post_request(self.__group_delete_path, headers=headers, payload=payload)
        return response

    # Working with numbers in group:
    def group_number_add(self, access_token, id_group, numbers):
        headers = {'X-Access-Token': access_token}
        headers.update(self.__headers)
        payload = {
            'id_group': id_group,
            'numbers': numbers
        }
        response = self._make_post_request(self.__group_num_add_path, headers=headers, payload=payload)
        return response

    def group_number_search(self, access_token, id_group, numbers):
        headers = {'X-Access-Token': access_token}
        headers.update(self.__headers)
        payload = {
            'id_group': id_group,
            'numbers': numbers
        }

        response = self._make_post_request(self.__group_num_search_path, headers=headers, payload=payload)
        return response

    def group_number_delete(self, access_token, id_group, numbers):
        headers = {'X-Access-Token': access_token}
        headers.update(self.__headers)
        payload = {
            'id_group': id_group,
            'numbers': numbers
        }
        response = self._make_post_request(self.__group_num_del_path, headers=headers, payload=payload)
        return response

    def send_bulk(self, access_token, sender_id, text, id_group, id_group_excluded=None, date_start=None,
                  time_start=None, time_stop=None, phone=None):
        headers = {'X-Access-Token': access_token}
        headers.update(self.__headers)
        payload = {
            'senderID': sender_id,
            'text': text,
            'id_group': id_group
        }
        if id_group_excluded is not None:
            payload.update({'id_group_excluded': id_group_excluded})
        if date_start is not None:
            payload.update({'dateStart': date_start})
        if time_start is not None:
            payload.update({'timeStart': time_start})
        if time_stop is not None:
            payload.update({'timeStop': time_stop})
        if phone is not None:
            payload.update({'phone': phone})

        response = self._make_post_request(self.__send_bulk_path, headers=headers, payload=payload)
        return response

    # Working with Personal Black List
    def black_list_add(self, access_token, numbers):
        headers = {'X-Access-Token': access_token}
        headers.update(self.__headers)
        payload = {
            'numbers': numbers
        }
        response = self._make_post_request(self.__blacklist_add_path, headers=headers, payload=payload)
        return response

    def black_list_search(self, access_token, numbers):
        headers = {'X-Access-Token': access_token}
        headers.update(self.__headers)
        payload = {
            'numbers': numbers
        }
        response = self._make_post_request(self.__blacklist_search_path, headers=headers, payload=payload)
        return response

    def black_list_delete(self, access_token, numbers):
        headers = {'X-Access-Token': access_token}
        headers.update(self.__headers)
        payload = {
            'numbers': numbers
        }
        response = self._make_post_request(self.__blacklist_del_path, headers=headers, payload=payload)
        return response

    # Logout (token destroy):
    def logout(self, access_token):
        headers = {'X-Access-Token': access_token}
        response = self._make_get_request(self.__logout_path, headers=headers)
        return response

    # Auxiliary functions:
    @staticmethod
    def _make_post_request(path, headers, payload):
        response = requests.post(path, headers=headers, json=payload)
        return response

    @staticmethod
    def _make_get_request(path, headers):
        response = requests.get(path, headers=headers)
        return response
