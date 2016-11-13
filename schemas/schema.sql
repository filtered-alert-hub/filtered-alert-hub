CREATE table subscriptions(
	subscriptionId varchar(50) primary key,
	subscriptionName varchar(100),
	subscriptionUrl varchar(200),
	languageOnly char(10),
	highPriorityOnly boolean,
	officialOnly boolean,
	xPathFilterId varchar(50),
	xPathFilter varchar(200),
	areaFilterId varchar(50),
	circleCenterRadius numeric,
	feed_rss_xml XML,
	geom geometry(Polygon,4326)
);