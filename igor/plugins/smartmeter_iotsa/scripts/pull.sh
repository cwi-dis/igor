#!/bin/bash

curl --silent http://$igor_host/p1?format=xml | igorVar --put application/xml sensors/smartMeter
