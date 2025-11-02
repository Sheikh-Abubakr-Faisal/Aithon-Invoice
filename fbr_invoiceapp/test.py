# import requests

# token = "2a7dd7c6-7160-3ff7-b360-b786bf7e24ba"
# headers = {
#     "Authorization": f"Bearer {token}"
# }

# url = "https://gw.fbr.gov.pk/dist/v1/Get_Reg_Type"

# # Pass the NTN as query parameter
# params = {
#     "Registration_No": "2454071"  # replace with real/test NTN
# }

# response = requests.get(url, headers=headers, params=params)  # <-- use params, not json

# print("Status Code:", response.status_code)
# print("Response Text:", response.text)
# try:
#     print("Response JSON:", response.json())
# except Exception as e:
#     print("Could not parse JSON:", e)


import requests

token = "2a7dd7c6-7160-3ff7-b360-b786bf7e24ba"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

url = "https://gw.fbr.gov.pk/dist/v1/statl"
params = {
    "regno": "2454071",
    "date": "2025-05-18"
}

response = requests.get(url, headers=headers, params=params)  # they use GET but need JSON body

print("Status Code:", response.status_code)
print("Response Text:", response.text)

try:
    print("Response JSON:", response.json())
except Exception as e:
    print("Could not parse JSON:", e)
