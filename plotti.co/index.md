---
layout: default
---

<script src="https://cdn.jsdelivr.net/jquery/3.0.0-beta1/jquery.min.js"></script>

Live plotting that **just works**.

<br/><object id="live1" data="http://plotti.co/plotti.co/plot.svg" type="image/svg+xml" style="width: 570px; height: 190px;"></object>

Plottico is a [microservice](https://en.wikipedia.org/wiki/Microservices) that generates live-streaming SVG-image plots to be embedded as an `<object>` tag of your web page. That simple.

<iframe src="https://ghbtns.com/github-btn.html?user=grandrew&amp;repo=plotti.co&amp;type=watch&amp;count=true&amp;size=large"
  allowtransparency="true" frameborder="0" scrolling="0" width="170" height="30"></iframe><br/>

## Usage

### Including live image in your page

To include a live plot on your webpage, you just need to put in an SVG image:

~~~html
<object data="http://plotti.co/YOUR_HASH/plot.svg" type="image/svg+xml"></object>
~~~

where `YOUR_HASH` is the hash you chose for your stream. We will use it in the following example to feed the data.

here it is:

<object id="yhimg" data="http://plotti.co/YOUR_HASH/plot.svg" type="image/svg+xml" style="width: 570px; height: 190px;"></object>


### Feeding the data to the image

You can try it by clicking here:

<a id="yhref" onclick="feed()">http://plotti.co/YOUR_HASH?d=,,2</a>

## Quick examples

### Server CPU load on plottico

~~~sh
#!/bin/sh
while true; do
wget -O /dev/null -q http://plotti.co/lock/plottycocpu?d=`mpstat -P ALL 1 1 | awk '/Average:/ && $2 ~ /[0-9]/ {print $3}' | sort -r -g | xargs | sed s/\ /,/g`\%cpuload
done
~~~

<object data="http://plotti.co/plottycocpu/plot.svg" type="image/svg+xml" style="width: 570px; height: 190px;"></object>

### Network load on plottico

~~~sh
#!/bin/sh
S=1; F=/sys/class/net/eth0/statistics/tx_bytes
while true; do
  X=`cat $F`; sleep $S; Y=`cat $F`; BPS="$(((Y-X)/S*8))";
  wget http://plotti.co/lock/plotticonet?d=${BPS}bps -q -O /dev/null
done
~~~

<object data="http://plotti.co/plotticonet/plot.svg" type="image/svg+xml" style="width: 570px; height: 190px;"></object>

### Current open connections

~~~sh
#!/bin/bash
while true; do
wget -O /dev/null -q http://plotti.co/lock/plotticonn?d=`netstat -tn | wc -l`sockets
sleep 1
done
~~~

<object data="http://plotti.co/plotticonn/plot.svg" type="image/svg+xml" style="width: 570px; height: 190px;"></object>

## Explanation

To feed some data into the stream, you just create a `GET` request of the following form:

~~~sh
$ wget "http://plotti.co/YOUR_HASH?d=1.5,3.6,7.8mbps" -O /dev/null
~~~

the format of the request is 

~~~
?d=[value_red],[value_blue],...
~~~

Where each `[value_X]` is a separate line drawn on the plot. You may optionally append units as short string to any of the data values to show it as "y" axis units or just as a general message.

### Choosing size

You can specify image size that you want your SVG to advertise:

~~~html
<object data="http://plotti.co/YOUR_HASH/WIDTHxHEIGHT.svg" type="image/svg+xml"></object>
~~~

where `WIDTH` and `HEIGHT` are width and height of the image respectively. Using a specified size makes any styling in the embedding document unnessessary.

### Choosing color

The microservice supports up to 9 inputs, each can be omitted at any time and each has its own color:

~~~css
.src0 {
    stroke: #5DA5DA; /* (blue) */
}
.src1 {
    stroke: #F15854; /* (red) */
}
.src2 {
    stroke: #DECF3F; /* (yellow) */
}
.src3 {
    stroke: #B276B2; /* (purple) */
}
.src4 {
    stroke: #B2912F; /* (brown) */
}
.src5 {
    stroke: #F17CB0; /* (pink) */
}
.src6 {
    stroke: #60BD68; /* (green) */
}
.src7 {
    stroke: #FAA43A; /* (orange) */
}
.src8 {
    stroke: #4D4D4D; /* (gray) */
}
~~~

for example, to use color `green` you only provide the 7th input: <a id="yhref2" onclick="feed2()">http://plotti.co/YOUR_HASH?d=,,,,,,1.0</a>

### No OBJECT tag

There are cases where the environment that you use does support images in documents but does not support `object` tags. In case you are allowed to add javascript to documents, here is the snippet that will convert all appropriate `<img>` tags to `<object>`:

~~~js
window.addEventListener("load", function load(event) {
    window.removeEventListener("load", load, false);
    var limg=document.getElementsByTagName("IMG");
    for(var il=0;il<limg.length;il++) {
        var s=limg[il].getAttribute("src");
        if(s.startsWith("http://plotti.co/")) {
            limg[il].outerHTML='<object data="'+s+'" type="image/svg+xml"></object>';
        }
    }
},false);
~~~

## Security

### Locking the single feeder

If you want to lock a single host IP address as a feeder of the data so that no other IP can send to your hash - you can use the path `http://plotti.co/lock/YOUR_HASH?d=1,2,3`. After executing this request the sender will be locked for this hash. The hash locks get dropped eventually, so keep using this address to continue holding the lock.

### HTTPS

HTTPS coming soon.

## Limitations

- Data feed rate is limited to 50 updates/sec per host. Please request if you need more
- You can not have more than 6 plots streaming in one browser (being worked on)
- There are some known [bugs](https://github.com/grandrew/plotti.co/issues)
- Microsoft Edge does not support EventSource yet

## Terms of serve and privacy

The service is provided as-is. Howerver we use our best efforts to make sure the service delivers best possible response times.

There are currenlty no plans to collect any personal information.

These terms are subject to change. Please follow me on [twitter](http://twitter.com/andrew_vrayo) to be notified of any planned changes.

## Pricing

Plotti.co microservice is free of charge; but if you like it and want to continue using on a regular basis please consider donating to support development and service uptime.

The recommended donations are 

 - $0.50 per month to show your interest in continued development and features
 - $3 per month if you estimate to have 100 clients watching the stream during the month
 - $10 per month if your data update rate exceeds 1 update/second for your 100 clients
 - $50 per month to ensure high-volume traffic is handled well by [plotti.co](http://plotti.co)

<form action="https://www.paypal.com/cgi-bin/webscr" method="post" target="_top">
<input type="hidden" name="cmd" value="_s-xclick">
<input type="hidden" name="encrypted" value="-----BEGIN PKCS7-----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-----END PKCS7-----
">
<input type="image" src="https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif" border="0" name="submit" alt="PayPal - The safer, easier way to pay online!">
<img alt="" border="0" src="https://www.paypalobjects.com/en_US/i/scr/pixel.gif" width="1" height="1">
</form>

[plotti.co](http://plotti.co)

## Roadmap

The features on the roadmap include storing some points in advance to be able to serve meaningful up-to-date plots in `<img>` tags, [https](https://github.com/grandrew/plotti.co/issues/4), more interaction, [more types of plots (pie,log,hist,gauges)](https://github.com/grandrew/plotti.co/issues/6), more beauty, etc.

Keep updated with [github](https://github.com/grandrew/plotti.co) issues!

## Author

Andrew Gryaznov ([in](https://www.linkedin.com/in/grandrew)/[GitHub](http://github.com/grandrew)/[Twitter](http://twitter.com/andrew_vrayo)).

![Andrew Gryaznov](https://en.gravatar.com/avatar/c0d7a528fe5e44aad0d1e81e8080db37.jpg?s=200)

You can send any feedback and suggestions to ag@vrayo.com or realgrandrew@gmail.com

### License

[AGPLv3 License](http://www.gnu.org/licenses/agpl-3.0.en.html)

<a href="https://github.com/grandrew/plotti.co" class="github-corner"><svg width="80" height="80" viewBox="0 0 250 250" style="fill:#151513; color:#fff; position: absolute; top: 0; border: 0; right: 0;"><path d="M0,0 L115,115 L130,115 L142,142 L250,250 L250,0 Z"></path><path d="M128.3,109.0 C113.8,99.7 119.0,89.6 119.0,89.6 C122.0,82.7 120.5,78.6 120.5,78.6 C119.2,72.0 123.4,76.3 123.4,76.3 C127.3,80.9 125.5,87.3 125.5,87.3 C122.9,97.6 130.6,101.9 134.4,103.2" fill="currentColor" style="transform-origin: 130px 106px;" class="octo-arm"></path><path d="M115.0,115.0 C114.9,115.1 118.7,116.5 119.8,115.4 L133.7,101.6 C136.9,99.2 139.9,98.4 142.2,98.6 C133.8,88.0 127.5,74.4 143.8,58.0 C148.5,53.4 154.0,51.2 159.7,51.0 C160.3,49.4 163.2,43.6 171.4,40.1 C171.4,40.1 176.1,42.5 178.8,56.2 C183.1,58.6 187.2,61.8 190.9,65.4 C194.5,69.0 197.7,73.2 200.1,77.6 C213.8,80.2 216.3,84.9 216.3,84.9 C212.7,93.1 206.9,96.0 205.4,96.6 C205.1,102.4 203.0,107.8 198.3,112.5 C181.9,128.9 168.3,122.5 157.7,114.1 C157.9,116.9 156.7,120.9 152.7,124.9 L141.0,136.5 C139.8,137.7 141.6,141.9 141.8,141.8 Z" fill="currentColor" class="octo-body"></path></svg></a><style>.github-corner:hover .octo-arm{animation:octocat-wave 560ms ease-in-out}@keyframes octocat-wave{0%,100%{transform:rotate(0)}20%,60%{transform:rotate(-25deg)}40%,80%{transform:rotate(10deg)}}@media (max-width:500px){.github-corner:hover .octo-arm{animation:none}.github-corner .octo-arm{animation:octocat-wave 560ms ease-in-out}}</style>

<script>
my_hash=Math.random()*100000000;
document.getElementById("live1").setAttribute("data", "http://plotti.co/"+my_hash+"/plot.svg");
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
    myImage.src = "http://plotti.co/"+my_hash+"?d="+y1+"rand,"+y2+","+y3;
    //console.log(myImage);
}
function makeid()
{
    var text = "";
    var possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";

    for( var i=0; i < 12; i++ )
        text += possible.charAt(Math.floor(Math.random() * possible.length));

    return text;
}
YH = makeid();

function feed() {
       
}

document.getElementById("yhimg").setAttribute("data", "http://plotti.co/"+YH+"/plot.svg");
document.getElementById("yhref").innerHTML="http://plotti.co/"+YH+"?d=,,2";
document.getElementById("yhref2").innerHTML="http://plotti.co/"+YH+"?d=,,,,,,1.0";
function feed() {
    var myImage = new Image(1, 1);
    myImage.src = "http://plotti.co/"+YH+"?d=,,2&h="+makeid();
    //console.log(myImage);
    return false;
}

function feed2() {
    var myImage = new Image(1, 1);
    myImage.src = "http://plotti.co/"+YH+"?d=,,,,,,1.0&h="+makeid();
    //console.log(myImage);
    return false;
}

$(".s").each(function () {
    $(this).html( $(this).html().replace("YOUR_HASH", YH) );
});

$(".highlighter-rouge").each(function () {
    $(this).html( $(this).html().replace("YOUR_HASH", YH) );
});




setInterval(pushData, 300);
</script>

<script>
  (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
  (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
  m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
  })(window,document,'script','//www.google-analytics.com/analytics.js','ga');

  ga('create', 'UA-75121462-1', 'auto');
  ga('send', 'pageview');

</script>
