#Syntax:
#target: prerequisites
#<TAB> recipe
#Refer https://opensource.com/article/18/8/what-how-makefile

.DEFAULT_GOAL := clean
MYNAME := "prathap"

run_fakemessages:
	@echo "Running fake messages pipeline"
	python3 -m launch_dfjob \
	--pipelinename="fake_messages"

run_psn:
	@echo "Running pubsubnotification pipeline"
	python3 -m launch_dfjob \
	--pipelinename="pubsubnotification"


#generate: clean
#	@echo "Creating empty text files... ${MYVAR}"

clean:
	@echo "Cleaning up..."
