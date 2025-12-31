# Strawberry AI

This is a voice assistant platform using a hub and spoke architecture.

The hub handles AI interaction and chat history, user accounts, sessions, etc. The spokes provide the voice interaction and other services. They are the devices that run the actual code to call a skill when the AI presents a skill call command. When the user requests that a skill be called ("Alexa, turn on all the lights" or "Jarvis, set the temperature to 72 degrees"), the spoke will: 
1. Present the user's input to the hub
2. The hub calls the actuall LLM (managed by TensorZero) and returns the response to the spoke
3. The spoke displays the output to the user, running skills if they are called (note: any response to a single prompt can result in multiple text outputs and skill calls. All are displayed to the user in the order they are returned by the LLM Agent.)

Each spoke contains: 1. The prompt engine (TensorZero, which sends requests to the Hub in the OpenAI format), 2. The skill runner (a completely separate component that will be discussed below). 

## The Skill Runner: 
The LLM will run Python code in a Pyodide sandbox, but the actual skill code runs in a full Python environment (allowing it to affect the device directly, like turning up the volume, turning on lights, making network requests, etc.). This way, the LLM can make complex skill calls or run many searches at once, but the device is protected from malicious external code.

The skill runner has 2 modes: remote and local. 
### Local Mode: 
In local mode, all skills are stored as Python files in a folder. For example, the user might make a music control skill, a class that contains `search_songs(query:str, max_results:int=10, include_lyrics:bool=False)->List[Song]`, `set_volume(volume:int)->None`, and functions to play and pause specific songs. The LLM is presented with the function signature and docstrings, not the internal code. Each skill is presented as a class. All instances of the class are loaded into the device class before the LLM is presented with the device class. It lets the LLM search for skill functions using common phrases (`device.search_skills(query:str="")`), get the function's information, function signature, and docstring (`get_skill_info(skill_name:str)->dict`), and run them (`device.MusicControlSkill.search_songs(query:str="")`). Local skills are stored in a folder on the device, and the skill runner loads them into the device class when the device is initialized.

Example output of `device.search_skills(query:str="")` in local mode. It returns the function name, parent class name, and the first line of the docstring (summary):
```python
[
    {
        "name": "search_songs",
        "parent_class": "MusicControlSkill",
        "summary": "Searches for songs in the music library"
    }
]
```

Example output of `device.get_function_info(function_name:str="search_songs")` in local mode. It returns the function signature and full docstring as a string.
```python
def search_songs(query:str, max_results:int=10, include_lyrics:bool=False)->List[Song]:
    """
    Searches for songs in the music library. Returns a list of songs.
    Args:
        query: The query to search for.
        max_results: The maximum number of results to return.
        include_lyrics: Whether to include lyrics in the results.
    Returns:
        A list of songs.
    """
```

### Remote Mode: 
In remote mode, skills are shared and called through the Hub's Skill Registry. It keeps track of which device a skill is hosted on, and which device is currently active. If two skills have the same name and parameters, it considers them the same skill on different devices.  For example, "turn on the volume on the TV" and "turn up the volume" imply the same skill, but one on a separate device and one on the current one. That way we can easily deploy skills on different devices by simply downloading the same code to the other device. The LLM's instruction prompt (provided by the Skill Runner) will include directions to assume the current device if no device is provided. 

A `search_skills()` function is provided to search for skills, and it returns a list of: skill function name, parent class name, and a list of devices that the skill is hosted on. By default, it puts results on the current device first. It can then call the skills using the same syntax as local mode. Example output of `search_skills(query:str="")` in remote mode:
```python
[
    {
        "name": "search_songs",
        "parent_class": "MusicControlSkill",
        "devices": ["TV", "Speaker"]
    },
    {
        "name": "set_volume",
        "parent_class": "DeviceControlSkill",
        "devices": ["TV", "Speaker"]
    }
]
```



The skill runner will call the Hub's skill registry to get the skill definitions and present them to the LLM. They are presented as if they were local functions, just like local mode, but they are actually remote functions that are called through the Hub's MQTT broker. The MQTT broker calls the skill server to run the skill code. 


## The Hub: 
Handling the MQTT broker: 
When a spoke registers its new skill, the skill registry saves it locally, including function signatures. Whenever a skill is called remotely, the skill runner can present the output as if it were a local function call. Devices are managed and duplicate skills on different devices are accounted for (defaulting to the current device). What can we do to present to the LLM that the skill exists on multiple devices in case it needs to run on a different device?

Presenting the skills to the LLM: 
Once the skill registry has its definitions, it forwards them to the LLM in a format that can be parsed by the skill runner. The skill runner can then present the skills to the LLM as if they were local functions. 