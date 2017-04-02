# Igor, your personal IoT butler
Igor is named after the Discworld characters of the same name. You should think of it as a butler (or valet, or majordomo, I am not quite sure of the difference) that knows everything that goes on in your household, and makes sure everything runs smoothly. It performs its tasks without passing judgements and maintains complete discretion, even within the household. It can work together with other Igors (lending a hand) and with lesser servants such as Iotsa-based devices.

## Technical description

Igor is basically a hierarchical data store, think of an XML file or a JSON file. Plugin modules for sensing devices modify the database (for example recording the fact such as _"device with MAC address 12:34:56:78:9a:bc has obtained an IP address from the DHCP service"_). Rules trigger on database changes and modify other entries in the database (for example _"if device 12:34:56:78:9a:bc is available then Jack is home"_ or _"If Jack is home the TV should be on"_). Action plugins also trigger on database changes and allow control over external hardware or software (for example _"If the TV should be on emit code 0001 to the infrared emitter in the living room"_).

## Comparison to other IoT solutions

Igor can be completely self-contained, it is not dependent on any cloud infrastructure. This means your thermostat should continue controlling your central heating even if the Google servers are down. Moreover, Igor allows you to keep information in-house, so you get to decide which information you share with whom. That said, Igor can work together with cloud services, so you can use devices for which vendor-based clouduse is the only option, but at least you get to combine this information with other sensor data.

Igor is primarily state-based, unlike ITTT (If This Then That) and many other IoT platforms which are primarily event-based. The advantage of state-based is that it allows you to abstract information more easily. In the example of the previous section, if you later decide to detect _"Jack is home"_ with a different method this does not affect the other rules. Moreover, you can give a person (or service) access the the state variable _"Jack is home"_ without giving them the MAC address of his phone.
