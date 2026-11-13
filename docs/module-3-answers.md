# Module 3 - Industrial Protocols: Modbus TCP and OPCUA

## Part A - Understanding the Data Model
See Self-check.txt for lessons learned

## Part B - Register Maps and Unit IDs

```
Inverter (INV)
------------------------------------------------------
| Addr | Ref         | Point      | Type     | Scale |
------------------------------------------------------
| 0-1  | 40001-40002 | AC_P_KW    | float32  | -     |
| 2-3  | 40003-40004 | DC_P_KW    | float32  | -     |
| 4    | 40005       | CAP_TEMP_C | int16    | 0.1   |
| 5    | 40006       | OPER_ST    | uint16   | 1     |
------------------------------------------------------

Meter (MTR)
--------------------------------------------------
| Addr | Ref         | Point   | Type    | Scale |
--------------------------------------------------
| 0-1  | 40001-40002 | AC_P_KW | float32 | -     |
--------------------------------------------------

Met Station (MET)
-----------------------------------------------
| Addr | Ref   | Point       | Type   | Scale |
-----------------------------------------------
| 0    | 40001 | POA_IRR_WM2 | uint16 | 0.1   |
| 1    | 40002 | AMB_TEMP_C  | int16  | 0.1   |
| 2    | 40003 | MOD_TEMP_C  | int16  | 0.1   |
-----------------------------------------------

Tracker (TRK)
-----------------------------------------------
| Addr | Ref   | Point       | Type   | Scale |
-----------------------------------------------
| 0    | 40001 | ANG_TGT_DEG | int16  | 0.01  |
| 1    | 40002 | ANG_ACT_DEG | int16  | 0.01  |
| 2    | 40003 | MODE_ST     | uint16 | 1     |
-----------------------------------------------

Unit IDs Assigned
----------------------------------------
| Unit IDs | Devices                   |
----------------------------------------
| 1-4      | SPS01_B01_INV01 ... INV04 |
| 5-8      | SPS01_B02_INV01 ... INV04 |
| 9-12     | SPS01_B01_TRK01 ... TRK04 |
| 13-16    | SPS01_B02_TRK01 ... TRK04 |
| 17       | SPS01_MTR01               |
| 18       | SPS01_MET01               |
----------------------------------------
```

## Part C - The Field Server: Python Modules for Module 3

```
 Field side: plantsim-field, or inside plantsim
|---------------------------|      |-------------------------|     |-----------------------------|
| Weather Model             |      | Device Models           |     | Field Server                |
|  Sun, clouds, temperature |----->|  8 INV, 8 TRK, MTR, MET |---->|  Unit IDs 1 to 18, one port |
|                           |      |                         |     | values computed per request |
| weather.py (unchanged)    |      | devices.py (unchanged)  |     | field.py (new)
|---------------------------|      |-------------------------|     |-----------------------------|
                                                                                    ^
                                               Modbus TCP, 127.0.0.1:5020           |
                                               function 03 requests and responses   |
                                                                                    |
      SCADA side: plantsim                                                          v
    |-----------------------|      |---------------------------|     |-----------------------------|
    | MariaDB               |      | TelemetryWriter           |     | ModbusPoller                |
    |  Telemetry table      |<-----|  batches, retries, spools |<----|  one connecteion per device |
    |                       |      |                           |     | one request per device map  |
    | db.py (unchanged)     |      | writer.py (unchanged)     |     | modbus_poller.py (new)      |
    |-----------------------|      |---------------------------|     |-----------------------------|
```

## Part D - The Modbus Client Run

$ pytest
=============================================================== test session starts ================================================================
platform linux -- Python 3.14.4, pytest-9.1.1, pluggy-1.7.0
rootdir: /home/jeanne/src/solar-plant-sim/python
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.16.0, cov-7.1.0, asyncio-1.4.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 45 items

tests/test_config.py ..                                                                                                                      [  4%]
tests/test_devices.py ........................                                                                                               [ 57%]
tests/test_modbus.py ...                                                                                                                     [ 64%]
tests/test_poller.py ...                                                                                                                     [ 71%]
tests/test_registers.py ......                                                                                                               [ 84%]
tests/test_weather.py ...                                                                                                                    [ 91%]
tests/test_writer.py ....                                                                                                                    [100%]

================================================================ 45 passed in 0.40s ================================================================

$ plantsim --config config/plant_m3.toml --hours 1
2026-11-12 09:50:28,237 INFO     plantsim: simulating SPS01 from 2026-10-12 11:00:00 to 2026-10-12 12:00:00 at 60x
2026-11-12 09:50:28,237 INFO     pymodbus.logging: Server listening.
2026-11-12 09:50:28,237 INFO     plantsim.field: field devices listening on 127.0.0.1:5020
2026-11-12 09:50:30,244 INFO     plantsim.writer: connected to database
2026-11-12 09:50:30,266 INFO     plantsim.writer: wrote 156 rows (total 156)
2026-11-12 09:50:32,269 INFO     plantsim.writer: wrote 177 rows (total 333)
...
2026-11-12 09:51:26,335 INFO     plantsim.writer: wrote 156 rows (total 4602)
2026-11-12 09:51:27,281 INFO     plantsim.writer: wrote 78 rows (total 4680)
2026-11-12 09:51:27,282 INFO     plantsim: done: 60 cycles, 4680 rows written, 0 spooled, 0 dropped, missed polls {}


## Part E - Run with tshark capture

```
# Terminal 1: start capture (-i lo -> loopback, -f -> specified filter, -w -> output file instead)
sudo tshark -i lo -f "tcp port 5020" -w /tmp/plantsim.pcapng

# Terminal 2: run 7 simulated hours, past the 17:00 comms outage
plantsim --config config/plant_m3.toml --hours 7

# Terminal 1, after plantsim finishes: Ctrl+C, then make the file yours (.pcapng is Wireshark's file format)
sudo chown $USER /tmp/plantsim.pcapng
```

Terminal 1:
$ sudo tshark -i lo -f "tcp port 5020" -w /tmp/plantsim.pcapng
Running as user "root" and group "root". This could be dangerous.
Capturing on 'Loopback: lo'
26009          # Note: this number counts up as the run proceeds landing on this final number at the end of the 7 hour run

Terminal 2:
$ plantsim --config config/plant_m3.toml --hours 7
2026-11-12 10:18:45,449 INFO     plantsim: simulating SPS01 from 2026-10-12 11:00:00 to 2026-10-12 18:00:00 at 60x
2026-11-12 10:18:45,450 INFO     pymodbus.logging: Server listening.
2026-11-12 10:18:45,450 INFO     plantsim.field: field devices listening on 127.0.0.1:5020
2026-11-12 10:18:47,455 INFO     plantsim.writer: connected to database
2026-11-12 10:18:47,468 INFO     plantsim.writer: wrote 156 rows (total 156)
2026-11-12 10:18:49,470 INFO     plantsim.writer: wrote 156 rows (total 312)
...
2026-11-12 10:25:44,482 INFO     plantsim.writer: wrote 78 rows (total 32680)
2026-11-12 10:25:44,482 INFO     plantsim: done: 420 cycles, 32680 rows written, 0 spooled, 0 dropped, missed polls {'SPS01_B01_INV02': 20}

Looking at the file produced by tshark capture:

$ tshark -r /tmp/plantsim.pcapng -d tcp.port==5020,mbtcp -Y modbus | head -20
   55 0.001773936    127.0.0.1 → 127.0.0.1    Modbus/TCP 78  unknown: Trans:     1; Unit:   1, Func:   3: Read Holding Registers. Unable to classify as query or response.
   57 0.001805316    127.0.0.1 → 127.0.0.1    Modbus/TCP 78  unknown: Trans:     1; Unit:   2, Func:   3: Read Holding Registers. Unable to classify as query or response.
   59 0.001825191    127.0.0.1 → 127.0.0.1    Modbus/TCP 78  unknown: Trans:     1; Unit:   3, Func:   3: Read Holding Registers. Unable to classify as query or response.
   61 0.001838482    127.0.0.1 → 127.0.0.1    Modbus/TCP 78  unknown: Trans:     1; Unit:   4, Func:   3: Read Holding Registers. Unable to classify as query or response.
   63 0.001850042    127.0.0.1 → 127.0.0.1    Modbus/TCP 78  unknown: Trans:     1; Unit:   5, Func:   3: Read Holding Registers. Unable to classify as query or response.
   65 0.001915302    127.0.0.1 → 127.0.0.1    Modbus/TCP 78  unknown: Trans:     1; Unit:   6, Func:   3: Read Holding Registers. Unable to classify as query or response.
   67 0.001962409    127.0.0.1 → 127.0.0.1    Modbus/TCP 78  unknown: Trans:     1; Unit:   7, Func:   3: Read Holding Registers. Unable to classify as query or response.
   69 0.001978807    127.0.0.1 → 127.0.0.1    Modbus/TCP 78  unknown: Trans:     1; Unit:   8, Func:   3: Read Holding Registers. Unable to classify as query or response.
   71 0.001992182    127.0.0.1 → 127.0.0.1    Modbus/TCP 78  unknown: Trans:     1; Unit:   9, Func:   3: Read Holding Registers. Unable to classify as query or response.
   73 0.002004365    127.0.0.1 → 127.0.0.1    Modbus/TCP 78  unknown: Trans:     1; Unit:  10, Func:   3: Read Holding Registers. Unable to classify as query or response.
   75 0.002014434    127.0.0.1 → 127.0.0.1    Modbus/TCP 78  unknown: Trans:     1; Unit:  11, Func:   3: Read Holding Registers. Unable to classify as query or response.
   77 0.002025768    127.0.0.1 → 127.0.0.1    Modbus/TCP 78  unknown: Trans:     1; Unit:  12, Func:   3: Read Holding Registers. Unable to classify as query or response.
   79 0.002036352    127.0.0.1 → 127.0.0.1    Modbus/TCP 78  unknown: Trans:     1; Unit:  13, Func:   3: Read Holding Registers. Unable to classify as query or response.
   81 0.002045926    127.0.0.1 → 127.0.0.1    Modbus/TCP 78  unknown: Trans:     1; Unit:  14, Func:   3: Read Holding Registers. Unable to classify as query or response.
   83 0.002055277    127.0.0.1 → 127.0.0.1    Modbus/TCP 78  unknown: Trans:     1; Unit:  15, Func:   3: Read Holding Registers. Unable to classify as query or response.
   85 0.002064096    127.0.0.1 → 127.0.0.1    Modbus/TCP 78  unknown: Trans:     1; Unit:  16, Func:   3: Read Holding Registers. Unable to classify as query or response.
   87 0.002074461    127.0.0.1 → 127.0.0.1    Modbus/TCP 78  unknown: Trans:     1; Unit:  17, Func:   3: Read Holding Registers. Unable to classify as query or response.
   89 0.002086833    127.0.0.1 → 127.0.0.1    Modbus/TCP 78  unknown: Trans:     1; Unit:  18, Func:   3: Read Holding Registers. Unable to classify as query or response.
   91 0.014055973    127.0.0.1 → 127.0.0.1    Modbus/TCP 87  unknown: Trans:     1; Unit:   2, Func:   3: Read Holding Registers. Unable to classify as query or response.
   93 0.015437295    127.0.0.1 → 127.0.0.1    Modbus/TCP 87  unknown: Trans:     1; Unit:   5, Func:   3: Read Holding Registers. Unable to classify as query or response.

Set environment variable CAP to shorten tshark commands. Although -d (decode-as) can be used to specify columns -o required
in CAP rather than -d because Response Time and Query are unknown with -d option.

    CAP="-r /tmp/plantsim.pcapng -o tcp.port==5020,mbtcp"

$ tshark $CAP -Y "modbus" -T fields -E header=y -e frame.time_relative -e mbtcp.trans_id -e mbtcp.unit_id -e modbus.func_code -e modbus.exception_code -e modbus.response_time | head -40
frame.time_relative     mbtcp.trans_id  mbtcp.unit_id   modbus.func_code        modbus.exception_code   modbus.response_time
0.001773936     1       1       3
0.001805316     1       2       3
0.001825191     1       3       3
0.001838482     1       4       3
0.001850042     1       5       3
0.001915302     1       6       3
0.001962409     1       7       3
0.001978807     1       8       3
0.001992182     1       9       3
0.002004365     1       10      3
0.002014434     1       11      3
0.002025768     1       12      3
0.002036352     1       13      3
0.002045926     1       14      3
0.002055277     1       15      3
0.002064096     1       16      3
0.002074461     1       17      3
0.002086833     1       18      3
0.014055973     1       2       3               0.012250657
0.015437295     1       5       3               0.013587253
0.017774950     1       3       3               0.015949759
0.017826195     1       9       3               0.015834013
0.019157696     1       11      3               0.017143262
0.019191582     1       7       3               0.017229173
0.020430391     1       18      3               0.018343558
0.020463670     1       1       3               0.018689734
0.025760239     1       10      3               0.023755874
0.025806267     1       6       3               0.023890965
0.033091933     1       8       3               0.031113126
0.034385070     1       12      3               0.032359302
0.037678105     1       14      3               0.035632179
0.037707628     1       15      3               0.035652351
0.043168320     1       13      3               0.041131968
0.046499213     1       4       3               0.044660731
0.048707346     1       17      3               0.046632885
0.048815487     1       16      3               0.046751391
1.001340466     2       1       3
1.001414889     2       2       3
1.001526855     2       3       3

## Part F - OPC UA Intro

F2. Core vocabulary
• Server / client: as in Modbus, but a client usually keeps one long-lived session with the server.
• Endpoint: the server's address, opc.tcp://host:4840/path. Port 4840 is the standard OPC UA port.
• Address space: the server's tree of nodes. Folders and objects group things (SPS01 → SPS01_MTR01); variables hold values (AC_P_KW).
• Namespace: a numbered group of node names, so two vendors' AC_P_KW can't collide. Index 0 is the OPC UA standard itself; your own nodes get an index such as 2.
• NodeId: a node's permanent identifier, written ns=2;i=3 (namespace 2, numeric id 3) or ns=2;s=SPS01/MTR01/AC_P_KW (string id). Ignition uses string ids built from tag paths.
• Browse name: the human-readable name used when walking the tree.
• DataValue: what a read returns: value, status code, source timestamp, server timestamp.
• Subscription and monitored item: instead of polling, the client asks the server to watch a node and report changes. A sampling interval says how often the server checks; a publishing interval says how often it sends the batched changes. If a value doesn't change, nothing is sent.
• Security policy and mode: whether messages are signed and encrypted, using certificates. Local demos run with None; real plants shouldn't.

Terminal 1:
$ plantsim-field

$ plantsim-field
2026-11-13 13:10:23,716 INFO     pymodbus.logging: Server listening.
2026-11-13 13:10:23,716 INFO     plantsim.field: field devices listening on 127.0.0.1:5020
2026-11-13 13:10:23,716 INFO     plantsim: unit   1  SPS01_B01_INV01
2026-11-13 13:10:23,716 INFO     plantsim: unit   2  SPS01_B01_INV02
2026-11-13 13:10:23,716 INFO     plantsim: unit   3  SPS01_B01_INV03
2026-11-13 13:10:23,716 INFO     plantsim: unit   4  SPS01_B01_INV04
2026-11-13 13:10:23,716 INFO     plantsim: unit   5  SPS01_B02_INV01
2026-11-13 13:10:23,716 INFO     plantsim: unit   6  SPS01_B02_INV02
2026-11-13 13:10:23,716 INFO     plantsim: unit   7  SPS01_B02_INV03
2026-11-13 13:10:23,716 INFO     plantsim: unit   8  SPS01_B02_INV04
2026-11-13 13:10:23,716 INFO     plantsim: unit   9  SPS01_B01_TRK01
2026-11-13 13:10:23,716 INFO     plantsim: unit  10  SPS01_B01_TRK02
2026-11-13 13:10:23,716 INFO     plantsim: unit  11  SPS01_B01_TRK03
2026-11-13 13:10:23,716 INFO     plantsim: unit  12  SPS01_B01_TRK04
2026-11-13 13:10:23,716 INFO     plantsim: unit  13  SPS01_B02_TRK01
2026-11-13 13:10:23,716 INFO     plantsim: unit  14  SPS01_B02_TRK02
2026-11-13 13:10:23,716 INFO     plantsim: unit  15  SPS01_B02_TRK03
2026-11-13 13:10:23,716 INFO     plantsim: unit  16  SPS01_B02_TRK04
2026-11-13 13:10:23,716 INFO     plantsim: unit  17  SPS01_MTR01
2026-11-13 13:10:23,716 INFO     plantsim: unit  18  SPS01_MET01

Terminal 2:
$ python tools/opcua_gateway.py

INFO     root: serving opc.tcp://127.0.0.1:4840/plantsim/

Terminal 3:

$ uals -u opc.tcp://127.0.0.1:4840/plantsim/ -n i=85 -d 3
WARNING:asyncua.client.client:Requested session timeout to be 3600000ms, got 600000ms instead
Browsing node i=85 at opc.tcp://127.0.0.1:4840/plantsim/

DisplayName                    NodeId                    BrowseName                Value

LocalizedText(Locale=None, Text='Locations') i=31915                   0:Locations
LocalizedText(Locale=None, Text='Server') i=2253                    0:Server
  LocalizedText(Locale=None, Text='ServerArray') i=2254                    0:ServerArray            , ['urn:freeopcua:python:server']
  LocalizedText(Locale=None, Text='NamespaceArray') i=2255                    0:NamespaceArray         , ['http://opcfoundation.org/UA/', 'urn:freeopcua:python:server', 'urn:plantsim']
  LocalizedText(Locale=None, Text='UrisVersion') i=15004                   0:UrisVersion            , None
  LocalizedText(Locale=None, Text='ServerStatus') i=2256                    0:ServerStatus           , ServerStatusDataType(StartTime=datetime.datetime(2026, 11, 13, 20, 10, 35, 715404, tzinfo=datetime.timezone.utc), CurrentTime=datetime.datetime(2026, 11, 13, 20, 13, 40, 990055, tzinfo=datetime.timezone.utc), State=<ServerState.Running: 0>, BuildInfo=BuildInfo(ProductUri='urn:freeopcua.github.io:python:server', ManufacturerName='FreeOpcUa', ProductName='FreeOpcUa Python Server', SoftwareVersion='1.0pre', BuildNumber='0', BuildDate=datetime.datetime(2026, 11, 13, 13, 10, 35, 713860, tzinfo=datetime.timezone.utc)), SecondsTillShutdown=0, ShutdownReason=LocalizedText(Locale=None, Text=None))
    LocalizedText(Locale=None, Text='StartTime') i=2257                    0:StartTime              , 2026-11-13 20:10:35.715404+00:00
    LocalizedText(Locale=None, Text='CurrentTime') i=2258                    0:CurrentTime            , 2026-11-13 20:13:40.990055+00:00
    LocalizedText(Locale=None, Text='State') i=2259                    0:State                  , 0
    LocalizedText(Locale=None, Text='BuildInfo') i=2260                    0:BuildInfo              , BuildInfo(ProductUri='urn:freeopcua.github.io:python:server', ManufacturerName='FreeOpcUa', ProductName='FreeOpcUa Python Server', SoftwareVersion='1.0pre', BuildNumber='0', BuildDate=datetime.datetime(2026, 11, 13, 13, 10, 35, 713860, tzinfo=datetime.timezone.utc))
    LocalizedText(Locale=None, Text='SecondsTillShutdown') i=2992                    0:SecondsTillShutdown    , None
    LocalizedText(Locale=None, Text='ShutdownReason') i=2993                    0:ShutdownReason         , None
  LocalizedText(Locale=None, Text='ServiceLevel') i=2267                    0:ServiceLevel           , 255
  LocalizedText(Locale=None, Text='Auditing') i=2994                    0:Auditing               , None
  LocalizedText(Locale=None, Text='EstimatedReturnTime') i=12885                   0:EstimatedReturnTime    , None
  LocalizedText(Locale=None, Text='LocalTime') i=17634                   0:LocalTime              , None
  LocalizedText(Locale=None, Text='ServerCapabilities') i=2268                    0:ServerCapabilities
    LocalizedText(Locale=None, Text='ServerProfileArray') i=2269                    0:ServerProfileArray     , None
    LocalizedText(Locale=None, Text='LocaleIdArray') i=2271                    0:LocaleIdArray          , None
    LocalizedText(Locale=None, Text='MinSupportedSampleRate') i=2272                    0:MinSupportedSampleRate , None
    LocalizedText(Locale=None, Text='MaxBrowseContinuationPoints') i=2735                    0:MaxBrowseContinuationPoints, None
    LocalizedText(Locale=None, Text='MaxQueryContinuationPoints') i=2736                    0:MaxQueryContinuationPoints, None
    LocalizedText(Locale=None, Text='MaxHistoryContinuationPoints') i=2737                    0:MaxHistoryContinuationPoints, None
    LocalizedText(Locale=None, Text='SoftwareCertificates') i=3704                    0:SoftwareCertificates   , None
    LocalizedText(Locale=None, Text='MaxArrayLength') i=11702                   0:MaxArrayLength         , None
    LocalizedText(Locale=None, Text='MaxStringLength') i=11703                   0:MaxStringLength        , None
    LocalizedText(Locale=None, Text='MaxByteStringLength') i=12911                   0:MaxByteStringLength    , None
    LocalizedText(Locale=None, Text='OperationLimits') i=11704                   0:OperationLimits
    LocalizedText(Locale=None, Text='ModellingRules') i=2996                    0:ModellingRules
    LocalizedText(Locale=None, Text='AggregateFunctions') i=2997                    0:AggregateFunctions
    LocalizedText(Locale=None, Text='MaxSessions') i=24095                   0:MaxSessions            , None
    LocalizedText(Locale=None, Text='MaxSubscriptions') i=24096                   0:MaxSubscriptions       , None
    LocalizedText(Locale=None, Text='MaxMonitoredItems') i=24097                   0:MaxMonitoredItems      , None
    LocalizedText(Locale=None, Text='MaxSubscriptionsPerSession') i=24098                   0:MaxSubscriptionsPerSession, None
    LocalizedText(Locale=None, Text='MaxMonitoredItemsPerSubscription') i=24104                   0:MaxMonitoredItemsPerSubscription, None
    LocalizedText(Locale=None, Text='MaxSelectClauseParameters') i=24099                   0:MaxSelectClauseParameters, None
    LocalizedText(Locale=None, Text='MaxWhereClauseParameters') i=24100                   0:MaxWhereClauseParameters, None
    LocalizedText(Locale=None, Text='MaxMonitoredItemsQueueSize') i=31916                   0:MaxMonitoredItemsQueueSize, None
    LocalizedText(Locale=None, Text='ConformanceUnits') i=24101                   0:ConformanceUnits       , None
    LocalizedText(Locale=None, Text='RoleSet') i=15606                   0:RoleSet
    LocalizedText(Locale=None, Text='HistoryServerCapabilities') i=11192                   0:HistoryServerCapabilities
  LocalizedText(Locale=None, Text='ServerDiagnostics') i=2274                    0:ServerDiagnostics
    LocalizedText(Locale=None, Text='ServerDiagnosticsSummary') i=2275                    0:ServerDiagnosticsSummary, None
    LocalizedText(Locale=None, Text='SamplingIntervalDiagnosticsArray') i=2289                    0:SamplingIntervalDiagnosticsArray, None
    LocalizedText(Locale=None, Text='SubscriptionDiagnosticsArray') i=2290                    0:SubscriptionDiagnosticsArray, None
    LocalizedText(Locale=None, Text='SessionsDiagnosticsSummary') i=3706                    0:SessionsDiagnosticsSummary
    LocalizedText(Locale=None, Text='EnabledFlag') i=2294                    0:EnabledFlag            , None
  LocalizedText(Locale=None, Text='VendorServerInfo') i=2295                    0:VendorServerInfo
  LocalizedText(Locale=None, Text='ServerRedundancy') i=2296                    0:ServerRedundancy
    LocalizedText(Locale=None, Text='RedundancySupport') i=3709                    0:RedundancySupport      , None
    LocalizedText(Locale=None, Text='RedundantServerArray') i=11313                   0:RedundantServerArray   , None
  LocalizedText(Locale=None, Text='Namespaces') i=11715                   0:Namespaces
    LocalizedText(Locale=None, Text='http://opcfoundation.org/UA/') i=15957                   0:http://opcfoundation.org/UA/
  LocalizedText(Locale=None, Text='GetMonitoredItems') i=11492                   0:GetMonitoredItems
    LocalizedText(Locale=None, Text='InputArguments') i=11493                   0:InputArguments         , [Argument(Name='SubscriptionId', DataType=NodeId(Identifier=7, NamespaceIndex=0, NodeIdType=<NodeIdType.Numeric: 2>), ValueRank=-1, ArrayDimensions=[], Description=LocalizedText(Locale=None, Text=None))]
    LocalizedText(Locale=None, Text='OutputArguments') i=11494                   0:OutputArguments        , [Argument(Name='ServerHandles', DataType=NodeId(Identifier=7, NamespaceIndex=0, NodeIdType=<NodeIdType.Numeric: 2>), ValueRank=1, ArrayDimensions=[0], Description=LocalizedText(Locale=None, Text=None)), Argument(Name='ClientHandles', DataType=NodeId(Identifier=7, NamespaceIndex=0, NodeIdType=<NodeIdType.Numeric: 2>), ValueRank=1, ArrayDimensions=[0], Description=LocalizedText(Locale=None, Text=None))]
  LocalizedText(Locale=None, Text='ResendData') i=12873                   0:ResendData
    LocalizedText(Locale=None, Text='InputArguments') i=12874                   0:InputArguments         , [Argument(Name='SubscriptionId', DataType=NodeId(Identifier=7, NamespaceIndex=0, NodeIdType=<NodeIdType.Numeric: 2>), ValueRank=-1, ArrayDimensions=[], Description=LocalizedText(Locale=None, Text=None))]
  LocalizedText(Locale=None, Text='SetSubscriptionDurable') i=12749                   0:SetSubscriptionDurable
    LocalizedText(Locale=None, Text='InputArguments') i=12750                   0:InputArguments         , [Argument(Name='SubscriptionId', DataType=NodeId(Identifier=7, NamespaceIndex=0, NodeIdType=<NodeIdType.Numeric: 2>), ValueRank=-1, ArrayDimensions=[], Description=LocalizedText(Locale=None, Text=None)), Argument(Name='LifetimeInHours', DataType=NodeId(Identifier=7, NamespaceIndex=0, NodeIdType=<NodeIdType.Numeric: 2>), ValueRank=-1, ArrayDimensions=[], Description=LocalizedText(Locale=None, Text=None))]
    LocalizedText(Locale=None, Text='OutputArguments') i=12751                   0:OutputArguments        , [Argument(Name='RevisedLifetimeInHours', DataType=NodeId(Identifier=7, NamespaceIndex=0, NodeIdType=<NodeIdType.Numeric: 2>), ValueRank=-1, ArrayDimensions=[], Description=LocalizedText(Locale=None, Text=None))]
  LocalizedText(Locale=None, Text='RequestServerStateChange') i=12886                   0:RequestServerStateChange
    LocalizedText(Locale=None, Text='InputArguments') i=12887                   0:InputArguments         , [Argument(Name='State', DataType=NodeId(Identifier=852, NamespaceIndex=0, NodeIdType=<NodeIdType.Numeric: 2>), ValueRank=-1, ArrayDimensions=[], Description=LocalizedText(Locale=None, Text=None)), Argument(Name='EstimatedReturnTime', DataType=NodeId(Identifier=13, NamespaceIndex=0, NodeIdType=<NodeIdType.Numeric: 2>), ValueRank=-1, ArrayDimensions=[], Description=LocalizedText(Locale=None, Text=None)), Argument(Name='SecondsTillShutdown', DataType=NodeId(Identifier=7, NamespaceIndex=0, NodeIdType=<NodeIdType.Numeric: 2>), ValueRank=-1, ArrayDimensions=[], Description=LocalizedText(Locale=None, Text=None)), Argument(Name='Reason', DataType=NodeId(Identifier=21, NamespaceIndex=0, NodeIdType=<NodeIdType.Numeric: 2>), ValueRank=-1, ArrayDimensions=[], Description=LocalizedText(Locale=None, Text=None)), Argument(Name='Restart', DataType=NodeId(Identifier=1, NamespaceIndex=0, NodeIdType=<NodeIdType.Numeric: 2>), ValueRank=-1, ArrayDimensions=[], Description=LocalizedText(Locale=None, Text=None))]
  LocalizedText(Locale=None, Text='Dictionaries') i=17594                   0:Dictionaries
  LocalizedText(Locale=None, Text='Quantities') i=32530                   0:Quantities
  LocalizedText(Locale=None, Text='DefaultHAConfiguration') i=32637                   0:DefaultHAConfiguration
    LocalizedText(Locale=None, Text='AggregateFunctions') i=32643                   0:AggregateFunctions
    LocalizedText(Locale=None, Text='Stepped') i=32644                   0:Stepped                , None
    LocalizedText(Locale=None, Text='Definition') i=32645                   0:Definition             , None
    LocalizedText(Locale=None, Text='MaxTimeInterval') i=32646                   0:MaxTimeInterval        , None
    LocalizedText(Locale=None, Text='MinTimeInterval') i=32647                   0:MinTimeInterval        , None
    LocalizedText(Locale=None, Text='ExceptionDeviation') i=32648                   0:ExceptionDeviation     , None
    LocalizedText(Locale=None, Text='ExceptionDeviationFormat') i=32649                   0:ExceptionDeviationFormat, None
    LocalizedText(Locale=None, Text='StartOfArchive') i=32650                   0:StartOfArchive         , None
    LocalizedText(Locale=None, Text='StartOfOnlineArchive') i=32656                   0:StartOfOnlineArchive   , None
    LocalizedText(Locale=None, Text='ServerTimestampSupported') i=32682                   0:ServerTimestampSupported, None
    LocalizedText(Locale=None, Text='MaxTimeStoredValues') i=32752                   0:MaxTimeStoredValues    , None
    LocalizedText(Locale=None, Text='MaxCountStoredValues') i=32753                   0:MaxCountStoredValues   , None
    LocalizedText(Locale=None, Text='AggregateConfiguration') i=32638                   0:AggregateConfiguration
  LocalizedText(Locale=None, Text='DefaultHEConfiguration') i=32754                   0:DefaultHEConfiguration
    LocalizedText(Locale=None, Text='EventTypes') i=32755                   0:EventTypes
    LocalizedText(Locale=None, Text='StartOfArchive') i=32756                   0:StartOfArchive         , None
    LocalizedText(Locale=None, Text='StartOfOnlineArchive') i=32757                   0:StartOfOnlineArchive   , None
  LocalizedText(Locale=None, Text='ServerConfiguration') i=12637                   0:ServerConfiguration
    LocalizedText(Locale=None, Text='ApplicationUri') i=25706                   0:ApplicationUri         , None
    LocalizedText(Locale=None, Text='ProductUri') i=25725                   0:ProductUri             , None
    LocalizedText(Locale=None, Text='ApplicationType') i=25707                   0:ApplicationType        , None
    LocalizedText(Locale=None, Text='ServerCapabilities') i=12710                   0:ServerCapabilities     , None
    LocalizedText(Locale=None, Text='SupportedPrivateKeyFormats') i=12639                   0:SupportedPrivateKeyFormats, None
    LocalizedText(Locale=None, Text='MaxTrustListSize') i=12640                   0:MaxTrustListSize       , None
    LocalizedText(Locale=None, Text='MulticastDnsEnabled') i=12641                   0:MulticastDnsEnabled    , None
    LocalizedText(Locale=None, Text='HasSecureElement') i=23597                   0:HasSecureElement       , None
    LocalizedText(Locale=None, Text='UpdateCertificate') i=13737                   0:UpdateCertificate
    LocalizedText(Locale=None, Text='ApplyChanges') i=12740                   0:ApplyChanges
    LocalizedText(Locale=None, Text='CancelChanges') i=25708                   0:CancelChanges
    LocalizedText(Locale=None, Text='CreateSigningRequest') i=12737                   0:CreateSigningRequest
    LocalizedText(Locale=None, Text='GetRejectedList') i=12777                   0:GetRejectedList
    LocalizedText(Locale=None, Text='ResetToServerDefaults') i=25709                   0:ResetToServerDefaults
    LocalizedText(Locale=None, Text='CertificateGroups') i=14053                   0:CertificateGroups
    LocalizedText(Locale=None, Text='TransactionDiagnostics') i=32336                   0:TransactionDiagnostics
    LocalizedText(Locale=None, Text='ConfigurationFile') i=15892                   0:ConfigurationFile
    LocalizedText(Locale=None, Text='KeyCredentialConfiguration') i=18155                   0:KeyCredentialConfiguration
    LocalizedText(Locale=None, Text='AuthorizationServices') i=17732                   0:AuthorizationServices
    LocalizedText(Locale=None, Text='UserManagement') i=24290                   0:UserManagement
  LocalizedText(Locale=None, Text='PublishSubscribe') i=14443                   0:PublishSubscribe
    LocalizedText(Locale=None, Text='GetSecurityKeys') i=15215                   0:GetSecurityKeys
    LocalizedText(Locale=None, Text='GetSecurityGroup') i=15440                   0:GetSecurityGroup
    LocalizedText(Locale=None, Text='SecurityGroups') i=15443                   0:SecurityGroups
    LocalizedText(Locale=None, Text='KeyPushTargets') i=25440                   0:KeyPushTargets
    LocalizedText(Locale=None, Text='SetSecurityKeys') i=17364                   0:SetSecurityKeys
    LocalizedText(Locale=None, Text='AddConnection') i=17366                   0:AddConnection
    LocalizedText(Locale=None, Text='RemoveConnection') i=17369                   0:RemoveConnection
    LocalizedText(Locale=None, Text='DataSetClasses') i=23685                   0:DataSetClasses
    LocalizedText(Locale=None, Text='SupportedTransportProfiles') i=17481                   0:SupportedTransportProfiles, None
    LocalizedText(Locale=None, Text='DefaultDatagramPublisherId') i=25480                   0:DefaultDatagramPublisherId, None
    LocalizedText(Locale=None, Text='ConfigurationVersion') i=25481                   0:ConfigurationVersion   , None
    LocalizedText(Locale=None, Text='DefaultSecurityKeyServices') i=32403                   0:DefaultSecurityKeyServices, None
    LocalizedText(Locale=None, Text='ConfigurationProperties') i=32404                   0:ConfigurationProperties, None
    LocalizedText(Locale=None, Text='PublishedDataSets') i=17371                   0:PublishedDataSets
    LocalizedText(Locale=None, Text='SubscribedDataSets') i=23658                   0:SubscribedDataSets
    LocalizedText(Locale=None, Text='PubSubConfiguration') i=25451                   0:PubSubConfiguration
    LocalizedText(Locale=None, Text='Status') i=17405                   0:Status
    LocalizedText(Locale=None, Text='Diagnostics') i=17409                   0:Diagnostics
    LocalizedText(Locale=None, Text='PubSubCapabilities') i=23678                   0:PubSubCapablities
  LocalizedText(Locale=None, Text='Resources') i=24226                   0:Resources
    LocalizedText(Locale=None, Text='Communication') i=24227                   0:Communication
    LocalizedText(Locale=None, Text='Logs') i=19378                   0:Logs
    LocalizedText(Locale=None, Text='ManagedApplications') i=16706                   0:ManagedApplications
    LocalizedText(Locale=None, Text='ProvisionableDevice') i=29878                   0:ProvisionableDevice
  LocalizedText(Locale=None, Text='ServerLog') i=19372                   0:ServerLog
    LocalizedText(Locale=None, Text='GetRecords') i=19373                   0:GetRecords
    LocalizedText(Locale=None, Text='MaxRecords') i=19376                   0:MaxRecords             , None
    LocalizedText(Locale=None, Text='MaxStorageDuration') i=19377                   0:MaxStorageDuration     , None
    LocalizedText(Locale=None, Text='MinimumSeverity') i=19751                   0:MinimumSeverity        , None
LocalizedText(Locale=None, Text='Aliases') i=23470                   0:Aliases
  LocalizedText(Locale=None, Text='FindAlias') i=23476                   0:FindAlias
    LocalizedText(Locale=None, Text='InputArguments') i=23477                   0:InputArguments         , [Argument(Name='AliasNameSearchPattern', DataType=NodeId(Identifier=12, NamespaceIndex=0, NodeIdType=<NodeIdType.Numeric: 2>), ValueRank=-1, ArrayDimensions=[], Description=LocalizedText(Locale=None, Text=None)), Argument(Name='ReferenceTypeFilter', DataType=NodeId(Identifier=17, NamespaceIndex=0, NodeIdType=<NodeIdType.Numeric: 2>), ValueRank=-1, ArrayDimensions=[], Description=LocalizedText(Locale=None, Text=None))]
    LocalizedText(Locale=None, Text='OutputArguments') i=23478                   0:OutputArguments        , [Argument(Name='AliasNodeList', DataType=NodeId(Identifier=23468, NamespaceIndex=0, NodeIdType=<NodeIdType.Numeric: 2>), ValueRank=1, ArrayDimensions=[0], Description=LocalizedText(Locale=None, Text=None))]
  LocalizedText(Locale=None, Text='LastChange') i=32852                   0:LastChange             , None
  LocalizedText(Locale=None, Text='TagVariables') i=23479                   0:TagVariables
    LocalizedText(Locale=None, Text='FindAlias') i=23485                   0:FindAlias
  LocalizedText(Locale=None, Text='Topics') i=23488                   0:Topics
    LocalizedText(Locale=None, Text='FindAlias') i=23494                   0:FindAlias
LocalizedText(Locale=None, Text='SPS01') ns=2;i=1                  2:SPS01
  LocalizedText(Locale=None, Text='SPS01_MTR01') ns=2;i=2                  2:SPS01_MTR01
    LocalizedText(Locale=None, Text='AC_P_KW') ns=2;i=3                  2:AC_P_KW                , 623.614990234375
  LocalizedText(Locale=None, Text='SPS01_MET01') ns=2;i=4                  2:SPS01_MET01
    LocalizedText(Locale=None, Text='POA_IRR_WM2') ns=2;i=5                  2:POA_IRR_WM2            , 271.6

$ uaread -u opc.tcp://127.0.0.1:4840/plantsim/ -n i=85 -p 2:SPS01,2:SPS01_MTR01,2:AC_P_KW
WARNING:asyncua.client.client:Requested session timeout to be 3600000ms, got 600000ms instead
915.5999755859375
