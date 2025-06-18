# Sisyphus by Monyet Python
Sisyphus is a desktop application that helps focus with users tasks and avoid procrastination. 
## Members
- Mikhail Maurice
- Aniq Asyraff
- Umar Mukhtar
- Haziq Naufal
- me
## Requirements
- npm ```active-win```. In the directory, ```cd frontend```, then ```npm install active-win```
- for backend, install all required Python libraries in ```requirements.txt```. 
From mikhail: Please use Python 3.10 for tensorflow compatibility. Download yolo.v4_weights, but do not commit! Run this in backend:
py -3.10 -m venv venv
pip install tensorflow opencv-python cvlib
## Usage
To run, ```frontend``` and ```backend``` must be active. <br>
- in the directory, ```cd frontend```, then run ```npm start```
- on a separate terminal, in the directory, ```cd backend``` then run ```uvicorn main:app --reload```
- at the root, create file ```.env``` and add ```GEMINI_API_KEY=[your gemini api key]```
<br>
Internet connection must be available to access Gemini AI services. <br>
By running this app, you agree to share essential datas to Gemini AI services to rate your current task.<br>
The camera does not share data with Gemini AI services.
<br>
 
![image](https://github.com/user-attachments/assets/9bb0ddc0-1434-489a-9d76-8671e2203624)
