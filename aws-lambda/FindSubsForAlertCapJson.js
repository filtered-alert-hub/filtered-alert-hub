console.log('Loading CAP event notifications');
var http = require('http');
var aws = require('aws-sdk');
// var s3 = new aws.S3({ apiVersion: '2006-03-01' });
console.log("OK GO");
/**
 * See https://nodejs.org/api/http.html#http_http_request_options_callback
 *
 * This handler accepts an event containing a GeoJson shape definition. Normally [tho not constrained so] this will
 * be a polygon or a circle. The handler will return a list of all subscriptions intersecting that alert profile.
 * Example events include
 *
 *  "polygonCoordinates": [
 *    [-109.5297,40.4554], [-109.5298,40.4556], [-109.5299,40.4556], [-109.5299,40.4554], [-109.5297,40.4554]
 *  ]
 *
 *
 *  "circleCenterRadius": [ -109.5288, 40.4555, 1000]
 *
 */
exports.handler = function(event, context) {
    // console.log("Event %o",event);
    console.log("Get xml2js 2");
    var xml2js = require('xml2js');
    var parseString = xml2js.parseString;
    var stripPrefix = null;
    try {
      var prefixMatch = new RegExp(/(?!xmlns)^.*:/);
      stripPrefix = function(str) {
        return str.replace(prefixMatch, '');
      };
    }
    catch ( err ) {
      console.log("Problem loading xml2js parse string %o",err);
    }
    var shape = null;
    var send_sns = 0;
    var alerts = [];
    var num_alerts = 1;
    var lambda_response = 'OK';
    var ctr = 0;
    if ( event.Records ) {
      console.log("Handle sns");
      num_alerts = event.Records.length;
      for (var i = 0; i < num_alerts; i++) {
        console.log("Pushing %o",event.Records[i].Sns.Message);
        var json_payload = JSON.parse(event.Records[i].Sns.Message);
        console.log("Parsed json payload");
          if ( json_payload.alert.capXml ) {
            console.log("SNS contains XML CAP Alert -- PARSE");
            parseString(json_payload.alert.capXml, {tagNameProcessors:[stripPrefix]}, function(err, result) {
              if ( err ) {
                console.log("Parsed XML payload err:%o",err);
              }
              if ( result ) {
                console.log("Got alert : result",result);
                alerts.push({orig:json_payload.alert,json:result});
              } 
            });
          }
          else if ( json_payload.alert.capJson ) {
            console.log("SNS contains JSON CAP Alert");
            alerts.push({orig:json_payload.alert,json:json_payload.alert.capJson});
          }
          else {
              console.log("SNS message does not contain capXml OR capJson -- cannot process");
          }
      }
      send_sns = 1;
    }
    else {
      console.log("Handle direct");
      // Direct event from http interface or test
      if ( ( event.alert ) && ( event.alert.capXML ) ) {
        parseString(event.alert.capXML, function(err, result) {
          alerts.push(result);
        });
      }
      else {
          console.log("After parsing XML, no capXML element found");
      }
    }
    var sns = send_sns ? new aws.SNS({region:'eu-west-1'}) : null;
    for (var i2 = 0; i2 < alerts.length; i2++) {
      var source_alert = alerts[i2].orig;
      var alert = alerts[i2].json;
      console.log("Processing -> (XML AS JSON) alert:",alert);
      var info_elements = alert.alert.info;
      // console.log("Processing info %o",info_elements);
      for ( var j=0; j<info_elements.length; j++ ) {
        // console.log("Process info element %o",info_elements[j]);
        var cap_area_elements = info_elements[j].area;
        for ( var k=0; k<cap_area_elements.length; k++ ) {
          // console.log("Process cap area %o %o",cap_area_elements[k]['areaDesc'],cap_area_elements[k]['polygon']);
          if ( cap_area_elements[k].polygon ) {
            var polygon_str = cap_area_elements[k].polygon[0];
            var polygon_arr = [];
            // String should be a sequence of space separated pairs, themselves split by a ,
            console.log("Process polygon_str",polygon_str);
            // Parse polygon into array of points consisting of lng lat comma separated
            var points_arr = polygon_str.split(' ');
            for ( var l = 0; l<points_arr.length; l++ ) {
              var lonlat = points_arr[l].split(',');
              // Flip the lon/lat due to geohash oddness
              polygon_arr.push([lonlat[1],lonlat[0]]);
            }
            shape = {
              "type": "polygon",
              "coordinates" : [ polygon_arr ]
            };
            // console.log("Setting up polygon shape : %o",shape);
          }
          else if ( cap_area_elements[k].circle ) {
              console.log("Circle");
              //  "$": "38.6138,-121.368 1"
              var circle_coords = cap_area_elements[k].circle[0];
              var circle_parts = circle_coords.split(' ');
              if (circle_parts.length == 2) {
                var coords = circle_parts[0].split(',');
                if ( coords.length == 2 ) {
                  // ES wants radius in meters -- odds are we are passed value in miles -- convert
                  var radius = parseInt(circle_parts[1]) * 1609.34; // 1609.34 meters in a mile
                  // Radius defaults to meters in ES
                  shape = {
                      "type":"circle",
                      "coordinates": [ coords[1], coords[0] ],
                      "radius": radius
                  };
                }
                else {
                    console.log("Unable to parse circle coords (got radius tho)"+circle_coords);
                }
              }
              else {
                console.log("Unable to parse circle coords+radius "+circle_coords);
              }
              
          }
          else {
            console.log("No polygon found");
          }
        }
      }
      if ( shape ) {
          
        console.log("Process shape %o",shape);
  
        var postData = JSON.stringify({
                         "from":0,
                         "size":1000,
                         "query":{
                           "bool": {
                             "must": {
                               "match_all": {}
                             },
                             "filter": {
                                 "geo_shape": {
                                   "subshape": {
                                     "shape": shape,
                                     "relation":'intersects'
                                   }
                                 }
                               }
                             }
                           },
                           "sort":{
                             "recid":{order:'asc'}
                           }
  
        });
  
        console.log("curl -X GET 'http://wah.semweb.co/es/alertssubscriptions/_search' -d '",postData,"'");
  
        var options = {
          hostname: 'wah.semweb.co',
          port: 80,
          json: true,
          body: postData,
          path: '/es/alertssubscriptions/_search',
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Content-Length': postData.length
          }
        };
  
        console.log("Create request");
        var req = http.request(options, function(res) {
            var body = '';
            console.log('Status:', res.statusCode);
            console.log('Headers:', JSON.stringify(res.headers));
            res.setEncoding('utf8');
            res.on('data', function(chunk) {
                body += chunk;
            });
  
            res.on('end', function() {
                console.log("Processing search response");
                // console.log('Successfully processed HTTP response');
                // If we know it's JSON, parse it
                if (res.headers['content-type'].lastIndexOf('application/json',0) === 0 ) {
                  body = JSON.parse(body);
                  var num_profiles = body.hits.hits.length;
  
                  // console.log("Processing %d profiles",num_profiles);
                  for (var i = 0; i < num_profiles; i++) {
                      
                    var profile_entry = body.hits.hits[i];
                    
                    console.log("Processing hit %d %s %s %s %s",i,profile_entry._source.name,profile_entry._source.recid,profile_entry._source.shortcode);
                    // Shape is in profile_entry._source.subshape
  
                    if ( send_sns ) {
                      ctr++;
                      var areaFilter = {};
                      if ( profile_entry._source.subshape.type === 'polygon' ) {
                        // Polygon
                        areaFilter.polygonCoordinates=profile_entry._source.subshape.coordinates;
                        areaFilter.circleCenterRadius="none";
                      }
                      else {
                        // circle centre radius
                        areaFilter.polygonCoordinates="none";
                        areaFilter.circleCenterRadius=profile_entry._source.subshape.coordinates;
                      }
                      var response_main = {
                        alert:source_alert,
                        subscription:{
                          subscriptionId:profile_entry._source.recid,
                          subscriptionName:profile_entry._source.name,
                          subscriptionUrl:profile_entry._source.subscriptionUrl,
                          languageOnly:profile_entry._source.languageOnly,
                          highPriorityOnly:profile_entry._source.highPriorityOnly,
                          officialOnly:profile_entry._source.officialOnly,
                          xPathFilterId:profile_entry._source.xPathFilterId,
                          xPathFilter:profile_entry._source.xPathFilter,
                          areaFilterId:profile_entry._source.areaFilterId,
                          shortcode:profile_entry._source.shortcode,
                          areaFilter:areaFilter
                        },
                      };
                      var response_json = {
                        default: JSON.stringify(response_main)
                      };
                      var response_payload = JSON.stringify(response_json);
                      try {
                        console.log("Publish profile alert message ", response_payload);
                        // Send sns for each matching sub
                        var pubResult = sns.publish({
                            Message: response_payload,
                            TopicArn: 'arn:aws:sns:eu-west-1:381798314226:wah_post-geofilter',
                            MessageStructure: 'json'
                        }, function(err, data) {
                            console.log("In sns.publish callback");
                            if (err) {
                              console.log("Problem ",err);
                              ctr--;
                              if ( ctr == 0 ) {
                                console.log("context.done");
                                context.done(null,"success");
                              }
                              else {
                                console.log("context not done ",ctr);
                              }
                            }
                            else {
                              console.log('Message sent ',data);
                              ctr--;
                              if ( ctr == 0 ) {
                                console.log("context.done");
                                context.done(null,"success");
                              }
                              else {
                                console.log("context not done ",ctr);
                              }
                            }
                        });
                        console.log("sns.publish completed cleanly");
                      }
                      catch(err) {
                        console.log("problem %o",err);
                      }
                      finally {
                        console.log("SNS Send complete ctr=",ctr);
                      }
                    }
                  }
                }
                else {
                  console.log("Unable to process response type %s",res.headers['content-type']);
                }
            });
        });
  
        // console.log("Sending http query %s",postData);
        req.on('error', function(e) {
          console.log("error %o",e);
          context.fail();
        });
        req.write(postData);
        // console.log("req.end");
        req.end();
        // console.log("Call completed");
      }
      else {
        // No shape to search against
        console.log("No shape to search against");
      }
    }
    console.log("Complete");
};
