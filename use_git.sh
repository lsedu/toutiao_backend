#!/bin/bash

#commit 变量
read -p "commit what?" OPTION
git add . && git commit -m "$OPTION"  && git push && echo -e "\033[33m push success! \033[0m \n" 

