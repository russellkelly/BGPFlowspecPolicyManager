flowspec:  build flowspec-container


build :
	docker build -t flowspec-manager .


flowspec-container:
	docker network create --driver=bridge --subnet=192.168.1.0/24 flowspec-net
	docker run -d -it --network=flowspec-net --ip=192.168.1.2 --dns=8.8.8.8 \
	--volume `pwd`:/home/flowspec \
	-p 179:179 \
	-p 2022:22 \
	-p 5000:5000 \
	-p 8008:8008 \
	-p 6343:6343/udp \
	--name flowspec-container flowspec-manager:latest
	docker exec flowspec-container tar -xvzf /home/flowspec/sflow-rt.tar.gz
	docker exec flowspec-container bash /home/flowspec/sflow-rt/get-app.sh sflow-rt mininet-dashboard
	docker exec flowspec-container bash /home/flowspec/sflow-rt/get-app.sh sflow-rt dashboard-example
	docker exec flowspec-container bash /home/flowspec/sflow-rt/get-app.sh sflow-rt flow-graph
	docker exec flowspec-container screen -dm bash /home/flowspec/sflow-rt/start.sh
	docker exec flowspec-container screen -dm exabgp /home/flowspec/ConfigFiles/exabgp.conf


clean:
	docker stop flowspec-container
	docker rm flowspec-container
	docker network rm flowspec-net

stop:
	docker stop flowspec-container

start:
	docker start flowspec-container
	docker exec flowspec-container screen -dm bash /home/flowspec/sflow-rt/start.sh
	docker exec flowspec-container screen -dm exabgp /home/flowspec/ConfigFiles/exabgp.conf
