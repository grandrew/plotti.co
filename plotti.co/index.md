---
layout: default
---

{::options parse_block_html="true" /}

Live plotting that **just works** <br/>and helps you fight with machines.

<br/><object data="https://plotti.co/random_sample" type="image/svg+xml" style="width: 570px; height: 190px;"/>

Plottico is a [microservice](https://en.wikipedia.org/wiki/Microservices) that generates live-streaming SVG-image plots to be embedded as an `<object>` tag.

<iframe src="https://ghbtns.com/github-btn.html?user=grandrew&amp;repo=plotti.co&amp;type=watch&amp;count=true&amp;size=large"
  allowtransparency="true" frameborder="0" scrolling="0" width="170" height="30"></iframe>

<div style="display: inline-block;" class="shares"><span class="shares"><a href="https://twitter.com/share" class="twitter-share-button" data-size="default" data-hashtags="plottico" style="display: inline-block;">Tweet</a></span>
</div>

<div class="shares" style="height: 31px; position: relative; top: -4px;">
<div class="fb-share-button" 
data-href="http://plotti.co" 
data-layout="button_count" style="display: inline-block;">
</div>
</div>

<br/>

*Now introducing Plottico Tracker website-to-website live plotting browser extension*

<a href="https://chrome.google.com/webstore/detail/plottico-tracker-pro/hjfkpgknlchgabgfhknaedgodmnhieep"><img src="https://doc.plotti.co/ChromeWebStore.png" style="width: 250px"/></a>

## Usage

### Including live image in your page

To include a live plot on your webpage, you just need to put in an SVG image:

~~~html
<object data="http://plotti.co/YOUR_HASH.svg" type="image/svg+xml"/>
~~~

where `YOUR_HASH.svg` is the hash you chose for your stream, `.svg` is optional. We will use it in the following example to feed the data.

here it is:

<object id="yhimg" data="https://plotti.co/YOUR_HASH/plot.svg" type="image/svg+xml" style="width: 400px; height: 100px;"></object>

You may also use a `<img src="http://plotti.co/YOUR_HASH.svg"/>` but in this case you won't get live updates, just a pre-cached plot with latest data.

### Feeding the data to the image programmatically

Just a simple GET to the same hash with an argument `d`:

~~~
http://plotti.co/YOUR_HASH.svg?d=<value>,<value>,...
~~~

You can try it by clicking here:

<a id="yhref" onclick="feed()">http://plotti.co/YOUR_HASH.svg?d=,,2</a>

### Feeding the data from external website

Use [Plottico Tracker Pro](https://chrome.google.com/webstore/detail/plottico-tracker-pro/hjfkpgknlchgabgfhknaedgodmnhieep) to send updates from websites to your favorite mission control dashboard using Chrome Web Browser.
No coding required.

<video width="600" height="420" autoplay loop>
  <source src="https://doc.plotti.co/plottico-mini.webm" type="video/webm" />
  <source src="https://doc.plotti.co/plottico-mini.mp4" type="video/mp4" />
  Your browser does not support the video tag.
</video>

### Get your data back

You can get latest submitted data by doing a GET to `https://plotti.co/YOUR_HASH/last`. Alternatively, you can use EventSource API directly to get the data in real-time, as it arrives. 
Here are [bash](https://doc.plotti.co/Bash-EventSource-API/) and [python](https://doc.plotti.co/Python-EventSource-API/) examples. It is extremely simple.

## Quick examples

### Server CPU load on plottico

~~~sh
#!/bin/sh
while true; do
wget -O /dev/null -q http://plotti.co/lock/plottycocpu?d=`mpstat -P ALL 1 1 | awk '/Average:/ && $2 ~ /[0-9]/ {print $3}' | sort -r -g | xargs | sed s/\ /,/g`\%cpuload
done
~~~

<img src="https://plotti.co/plottycocpu" style="width: 570px; height: 190px;"/>

### Bitcoin price

Fed using [Plottico Tracker Pro](https://chrome.google.com/webstore/detail/plottico-tracker-pro/hjfkpgknlchgabgfhknaedgodmnhieep) from [preev.com](http://preev.com) with 5-minute update interval.

<img src="https://plotti.co/1s2zHX59Wazn" style="width: 570px; height: 190px;"/>

### More examples

More examples like [linux network load](https://doc.plotti.co/Network-TX-Load-Linux/), [linux open sockets](https://doc.plotti.co/Established-Connections/) and many other integrations like [python feed](https://doc.plotti.co/Python-Snip/) - can be found in the plottico [copy-paste snippets portal](https://doc.plotti.co).

## Explanation

To feed some data into the stream, you just create a `GET` request of the following form:

~~~sh
$ wget "http://plotti.co/YOUR_HASH?d=1.5,3.6,7.8,mbps" -O /dev/null
~~~

the format of the request is 

~~~
?d=[value_blue],[value_red],...
~~~

Where each `[value_X]` is a separate line drawn on the plot. You may optionally append units as short string to the list or to any of the data values to show it as "y" axis units or just as a general message.

### Choosing size

You can specify image size that you want your SVG to advertise:

~~~html
<object data="https://plotti.co/YOUR_HASH/WIDTHxHEIGHT.svg" type="image/svg+xml"></object>
~~~

where `WIDTH` and `HEIGHT` are width and height of the image respectively. Using a specified size makes any styling in the embedding document unnessessary.

### Choosing color

The microservice supports up to 9 inputs, each can be omitted at any time and each has its own color:

~~~css
.src0 { stroke: #5DA5DA; /* (blue) */   }
.src1 { stroke: #F15854; /* (red) */    }
.src2 { stroke: #DECF3F; /* (yellow) */ }
.src3 { stroke: #B276B2; /* (purple) */ }
.src4 { stroke: #B2912F; /* (brown) */  }
.src5 { stroke: #F17CB0; /* (pink) */   }
.src6 { stroke: #60BD68; /* (green) */  }
.src7 { stroke: #FAA43A; /* (orange) */ }
.src8 { stroke: #4D4D4D; /* (gray) */   }
~~~

for example, to use color `green` you only provide the 7th input: <a id="yhref2" onclick="feed2()">http://plotti.co/YOUR_HASH?d=,,,,,,1.0</a>

### No OBJECT tag

There are cases where the environment that you use does support images in documents but does not support `object` tags. In case you are allowed to add javascript to documents, [here](https://doc.plotti.co/Convert-IMG-to-OBJECT/) is the snippet that will convert all relevant `<img>` tags to `<object>`. You can also embed as `iframe` with the same result.

## Security

### Locking the single feeder

If you want to lock a single host IP address as a feeder of the data so that no other IP can send to your hash - you can use the path `http://plotti.co/lock/YOUR_HASH?d=1,2,3`. After executing this request the sender will be locked for this hash. The hash locks get dropped eventually, so keep using this address to continue holding the lock.

Alternatively, plottico supports `&k=KEY` request parameter to lock to specified key. Use as `wget -q -O /dev/null "http://plotti.co/YOUR_HASH?d=1,2,3&k=YOUR_KEY"`.

For all the requests I recommend using encrypted connection using HTTPS.

## Limitations

- Your cached data will be deleted after about 1 day of idling (no updates or views)
- The server will drop IP address locks on restart
- There are some known bugs in [plottico](https://github.com/grandrew/plotti.co/issues) and in [tracker](https://github.com/grandrew/plotticotrack/issues)

## Terms of service and privacy

The service is provided as-is. However we use our best efforts to make sure the service delivers best possible response times.
By using Plottico Tracker Pro you agree to be responsible for any damages to third parties in case of violating their licenses.

There are currenlty no plans to collect any personal information.

These terms are subject to change. Please follow me on [twitter](http://twitter.com/andrew_vrayo) to be notified of any planned changes.

## Pricing

[Plotti.co microservice](https://plotti.co) and [Plotti.co Tracker Pro](https://chrome.google.com/webstore/detail/plottico-tracker-pro/hjfkpgknlchgabgfhknaedgodmnhieep) chrome extension are free of charge; but if you like it and want to continue using on a regular basis please consider donating to support development and service uptime.

<a class="coinbase-button" data-code="d38bfd90da7cddefacb5eb3929f8a53c" data-button-style="donation_large" href="https://www.coinbase.com/checkouts/d38bfd90da7cddefacb5eb3929f8a53c">Donate Bitcoins</a><script src="https://www.coinbase.com/assets/button.js" type="text/javascript"></script>

## Author

Andrew Gryaznov ([in](https://www.linkedin.com/in/grandrew)/[GitHub](http://github.com/grandrew)/[Twitter](http://twitter.com/andrew_vrayo)).

![Andrew Gryaznov](https://en.gravatar.com/avatar/c0d7a528fe5e44aad0d1e81e8080db37.jpg?s=200)

You can send any feedback and suggestions to [ag@vrayo.com](mailto:ag@vrayo.com)

### License

[AGPLv3 License](http://www.gnu.org/licenses/agpl-3.0.en.html) for the [microservice](https://github.com/grandrew/plotti.co) and [GPLv3 License](http://www.gnu.org/licenses/gpl-3.0.en.html) for the [tracker](https://github.com/grandrew/plotticotrack).

<a href="https://github.com/grandrew/plotti.co" class="github-corner"><svg width="80" height="80" viewBox="0 0 250 250" style="fill:#151513; color:#fff; position: absolute; top: 0; border: 0; right: 0;"><path d="M0,0 L115,115 L130,115 L142,142 L250,250 L250,0 Z"></path><path d="M128.3,109.0 C113.8,99.7 119.0,89.6 119.0,89.6 C122.0,82.7 120.5,78.6 120.5,78.6 C119.2,72.0 123.4,76.3 123.4,76.3 C127.3,80.9 125.5,87.3 125.5,87.3 C122.9,97.6 130.6,101.9 134.4,103.2" fill="currentColor" style="transform-origin: 130px 106px;" class="octo-arm"></path><path d="M115.0,115.0 C114.9,115.1 118.7,116.5 119.8,115.4 L133.7,101.6 C136.9,99.2 139.9,98.4 142.2,98.6 C133.8,88.0 127.5,74.4 143.8,58.0 C148.5,53.4 154.0,51.2 159.7,51.0 C160.3,49.4 163.2,43.6 171.4,40.1 C171.4,40.1 176.1,42.5 178.8,56.2 C183.1,58.6 187.2,61.8 190.9,65.4 C194.5,69.0 197.7,73.2 200.1,77.6 C213.8,80.2 216.3,84.9 216.3,84.9 C212.7,93.1 206.9,96.0 205.4,96.6 C205.1,102.4 203.0,107.8 198.3,112.5 C181.9,128.9 168.3,122.5 157.7,114.1 C157.9,116.9 156.7,120.9 152.7,124.9 L141.0,136.5 C139.8,137.7 141.6,141.9 141.8,141.8 Z" fill="currentColor" class="octo-body"></path></svg></a><style>.github-corner:hover .octo-arm{animation:octocat-wave 560ms ease-in-out}@keyframes octocat-wave{0%,100%{transform:rotate(0)}20%,60%{transform:rotate(-25deg)}40%,80%{transform:rotate(10deg)}}@media (max-width:500px){.github-corner:hover .octo-arm{animation:none}.github-corner .octo-arm{animation:octocat-wave 560ms ease-in-out}}</style>

<script>
my_hash=Math.random()*100000000;
// document.getElementById("live1").setAttribute("data", "https://plotti.co/"+my_hash+"/plot.svg");
y1=0
y2=0
y3=0
function pushData() {
    y1+=Math.random()*2-1;
    y2+=Math.random()*2-1;
    y3+=Math.random()*2-1;
    if(y1<0)y1=0;
    if(y2<0)y2=0;
    if(y3<0)y3=0;
    var myImage = new Image(1, 1);
    myImage.src = "https://plotti.co/"+my_hash+"?d="+y1+"rand,"+y2+","+y3;
    //console.log(myImage);
}
function makeid()
{
    var text = "";
    var possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";

    for( var i=0; i < 6; i++ )
        text += possible.charAt(Math.floor(Math.random() * possible.length));

    return text;
}
YH = makeid();

document.getElementById("yhimg").setAttribute("data", "https://plotti.co/"+YH+"/plot.svg");
document.getElementById("yhref").innerHTML="http://plotti.co/"+YH+".svg?d=,,2";
document.getElementById("yhref2").innerHTML="http://plotti.co/"+YH+".svg?d=,,,,,,1.0";
function feed() {
    var myImage = new Image(1, 1);
    myImage.src = "https://plotti.co/"+YH+"?d=,,2&h="+makeid();
    //console.log(myImage);
    return false;
}

function feed2() {
    var myImage = new Image(1, 1);
    myImage.src = "https://plotti.co/"+YH+"?d=,,,,,,1.0&h="+makeid();
    //console.log(myImage);
    return false;
}

$(".s").each(function () {
    $(this).html( $(this).html().replace("YOUR_HASH", YH) );
});

$(".highlighter-rouge").each(function () {
    $(this).html( $(this).html().replace("YOUR_HASH", YH) );
});

window.addEventListener("load", function load(event) {
    window.removeEventListener("load", load, false);
    setInterval(function() { var limg = document.getElementsByTagName("IMG");
    var r = new RegExp("^(http:|https:|)\/\/plotti.co");
    for(var il=0; il<limg.length; il++) {
        var s = limg[il].getAttribute("src"); if(r.test(s)) {
            var p = limg[il].parentNode; var st = limg[il].getAttribute("style");
            var cl = limg[il].getAttribute("class");
            var o = document.createElement("object");
            o.setAttribute("data", s); o.setAttribute("type", "image/svg+xml");
            o.setAttribute("class", cl); o.setAttribute("style", st);
            p.replaceChild(o,limg[il]);}}}, 1000); },false);

//setInterval(pushData, 300);
</script>

<script>
  (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
  (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
  m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
  })(window,document,'script','//www.google-analytics.com/analytics.js','ga');

  ga('create', 'UA-75121462-1', 'auto');
  ga('send', 'pageview');

</script>
<div id="fb-root"></div>
<script>(function(d, s, id) {
var js, fjs = d.getElementsByTagName(s)[0];
if (d.getElementById(id)) return;
js = d.createElement(s); js.id = id;
js.src = "//connect.facebook.net/en_US/all.js#xfbml=1";
fjs.parentNode.insertBefore(js, fjs);
}(document, 'script', 'facebook-jssdk'));</script>
