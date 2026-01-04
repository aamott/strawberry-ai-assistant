On Windows in particular, when you use Ctrl+C to stop a FastAPI server, it doesn't always work. It's most likely an issue where the children don't all exit when the parent does and in Windows it doesn't force kill the children. the`--reload` flag doesn't work at all in Windows or Linux. 

Some ideas are listed in this reddit page, but none of them are perfect. 
- https://www.reddit.com/r/learnpython/comments/1bttcss/are_you_able_to_exit_fastapiuvicorn_via_ctrlc_in/