var ntdrt = ntdrt || {};

ntdrt.application = {

    logScrollEnabled: true,

    init: function () {
        var self = ntdrt.application;
        self.relativeAppPrefix = ntdrt.appPrefix;
        if (self.relativeAppPrefix === '/') {
            self.relativeAppPrefix = '';
        }

        $(document).on('click', '[data-confirm]', function (e) {
            return confirm($(this).attr('data-confirm'));
        });

        var adjustNavigationPlaceholder = function () {
            var navigation = $('.navbar');
            var placeholder = $('.navbar-placeholder');
            var height = navigation.outerHeight() + 20;
            placeholder.css('height', height + 'px');
        };
        $(window).on('resize', adjustNavigationPlaceholder);
        adjustNavigationPlaceholder();

        $(document).on('click', '.toggle-navigation', function (e) {
            e.preventDefault();
            var target = $('.navbar > .container > .nav');
            if (target.is(':visible')) {
                target.slideUp(250);
            } else {
                target.slideDown(250);
            }
        });

        $(document).on('click', '.toggle-form', function (e) {
            e.preventDefault();
            var target = $('.navbar > .container > .navbar-form');
            if (target.is(':visible')) {
                target.slideUp(250);
            } else {
                target.slideDown(250);
            }
        });

        $(window).on('resize', function () {
            if ($(window).width() >= 992) {
                var targets = $('.navbar > .container > .nav, .navbar > .container > .navbar-form');
                targets.each(function () {
                    var target = $(this);
                    if (!target.is(':visible')) {
                        target.css('display', '');
                    }
                });
            }
        });

        $(document).on('change', '.setup select[name="version"]', function (e) {
            var control = $(this);
            var version = control.val();
            if (version.indexOf('TC') === 0 && version.indexOf('USB') === -1) {
                $('.setup [data-serial]').hide();
                $('.setup [data-ble]').show();
            } else {
                $('.setup [data-serial]').show();
                $('.setup [data-ble]').hide();
            }
        });

        $(document).on('click', '.setup-link', function (e) {
            e.preventDefault();
            var link = $(this).attr('href');
            var parts = [];
            var data = self.collect_connection_data();
            for (var name in data) {
                parts.push(name + '=' + encodeURIComponent(data[name]));
            }
            var sep = link.indexOf('?') === -1 ? '?' : '&';
            window.location.href = link + sep + parts.join('&');
        });

        $(document).on('click', 'button[data-import]', function () {
            var control = $(this);
            setTimeout(function () {
                control.prop('disabled', true);
                control.text('Importing...');
            }, 0);
        });

        var logWrapper = $('#log');
        var previousLogPosition = 0;
        logWrapper.on('scroll', function () {
            var position = logWrapper.scrollTop();
            if (previousLogPosition > position) {
                self.logScrollEnabled = false;
            } else if (!self.logScrollEnabled) {
                var mostBottomPosition = logWrapper.find('pre').outerHeight(true) - logWrapper.height();
                if (position === mostBottomPosition) {
                    self.logScrollEnabled = true;
                }
            }
            previousLogPosition = position;
        });

        self.connection();
        self.log();
        self.current();

        self.graph();
    },

    socket: null,
    connection: function () {
        var self = this;

        var url = location.protocol + '//' + location.host;
        var socket = self.socket = io.connect(url, {path: self.relativeAppPrefix + '/socket.io'});

        var newConnection = false;
        socket.on('connecting', function () {
            newConnection = false;
            $('#status').text('Connecting');
            self.disable(true);
            $('#connect button').text('Disconnect');
        });

        socket.on('connected', function () {
            newConnection = true;
            $('#status').text('Connected');
        });

        socket.on('disconnecting', function () {
            $('#status').text('Disconnecting');
        });

        socket.on('disconnected', function () {
            $('#status').text('Disconnected');
            self.disable(false);
            $('#connect button').text('Connect');
        });

        socket.on('update', function () {
            if (newConnection) {
                window.location.href = self.relativeAppPrefix + '/graph?session=';
            }
        });

        socket.on('log-error', function () {
            window.location.href = self.relativeAppPrefix + '/';
        });

        $(document).on('submit', '#connect', function (e) {
            var form = $(e.target);
            var input = form.find('[name="version"]');
            if (input.is(':disabled')) {
                socket.emit('close');
            } else {
                self.connect();
            }
            return false;
        });

        $(document).on('click', '.serial [data-connect]', function (e) {
            e.preventDefault();
            var port = $('.serial input[name="port"]').val();
            self.connect({port: port});
        });

        var serial = function () {
            socket.emit('scan_serial');
            $('.scan-result').text('Scanning... This can take a while...');
        };
        $(document).on('click', '.serial .scan button', serial);
        if ($('.serial .scan').length) {
            serial();
        }

        var ble = function () {
            socket.emit('scan_ble');
            $('.scan-result').text('Scanning... This can take a while...');
        };
        $(document).on('click', '.ble .scan button', ble);
        if ($('.ble .scan').length) {
            ble();
        }

        socket.on('scan-result', function (result) {
            $('.scan-result').html("<pre>" + result + "</pre>");
        });

        $(document).on('click', '.serial .scan-result [data-address]', function (e) {
            e.preventDefault();
            $('.scan-result').empty();
            self.connect({port: $(this).attr('data-address')});
        });

        $(document).on('click', '.ble .scan-result [data-address]', function (e) {
            e.preventDefault();
            $('.scan-result').empty();
            self.connect({ble_address: $(this).attr('data-address')});
        });
    },

    collect_connection_data: function () {
        var form = $('#connect');
        return {
            version: form.find('[name="version"]').val(),
            port: form.find('[name="port"]').val(),
            rate: form.find('[name="rate"]').val(),
            name: form.find('[name="name"]').val()
        };
    },

    connect: function (override) {
        var self = this;

        var data = self.collect_connection_data();
        if (override) {
            for (var name in override) {
                if (override.hasOwnProperty(name)) {
                    data[name] = override[name];
                }
            }

            var form = $('#connect');
            if (override.hasOwnProperty('port')) {
                form.find('[data-ble]').hide();
                var serial = form.find('[data-serial]');
                serial.show();
                serial.find('.setup-link').text(data['port']);

            } else if (override.hasOwnProperty('ble_address')) {
                form.find('[data-serial]').hide();
                var ble = form.find('[data-ble]');
                ble.show();
                ble.find('.setup-link').text(data['ble_address']);
            }
        }

        data = JSON.stringify(data);
        self.socket.emit('open', data);
        return data;
    },

    log: function () {
        var self = this;
        if ($('#log').length) {
            self.socket.on('log', function (message) {
                $('#log pre').append(message);
                if (self.logScrollEnabled) {
                    self.logScroll(500);
                }
            });

            $(window).on('resize', self.logResize);
            self.logResize();
            self.logScroll(0);
        }
    },

    chartLeft: null,
    chartRight: null,
    left_axis: null,
    right_axis: null,
    chart_buffer: [],
    current: function () {
        var self = this;
        var current = $('#current');
        if (current.length) {
            self.socket.on('update', function (message) {
                var data = JSON.parse(message);
                var counter = 0;
                current.find('td').each(function () {
                    $(this).text(data['table'][counter]);
                    counter++;
                });

                if (self.chartLeft && self.chartRight) {
                    self.chart_buffer.push(data);

                    // flush less often for huge datasets to minimize lag
                    var chart_size = self.chartLeft.data.length;
                    var buffer_size = self.chart_buffer.length;
                    if (chart_size > 1000 && buffer_size < 5) {
                        return;
                    }
                    if (chart_size > 10000 && buffer_size < 10) {
                        return;
                    }
                    if (chart_size > 100000 && buffer_size < 60) {
                        return;
                    }

                    try {
                        var items = [];
                        for (var index in self.chart_buffer) {
                            data = self.chart_buffer[index];
                            var item = {
                                date: data['graph']['timestamp'],
                            };
                            var push = false;
                            if (self.left_axis && data['graph'].hasOwnProperty(self.left_axis)) {
                                item['left'] = data['graph'][self.left_axis];
                                push = true;
                            }
                            if (self.right_axis && data['graph'].hasOwnProperty(self.right_axis)) {
                                item['right'] = data['graph'][self.right_axis];
                                push = true;
                            }
                            if (push) {
                                items.push(item);
                            }
                        }
                        if (items.length) {
                            self.chartLeft.data.pushAll(items);
                            self.chartRight.data.pushAll(items);
                        }
                    } catch (e) {
                        // ignore
                    }
                    self.chart_buffer = [];
                }
            });
        }
    },

    graph: function () {
        var self = this;
        var chartRoot = null;
        var graph = $('#graph');
        if (graph.length) {
            var create = function () {
                if (chartRoot) {
                    chartRoot.dispose();
                }

                graph.parent().find('.loading').show();

                var session = $('select[name="session"]').val();

                var left_axis = self.left_axis = $('select[name="left_axis"]').val();
                var left_name = $('#graph-settings option[value="' + left_axis + '"]').first().text();
                var right_axis = self.right_axis = $('select[name="right_axis"]').val();
                var right_name = $('#graph-settings option[value="' + right_axis + '"]').first().text();

                var colorsMode = $('select[name="colors"]').val();

                var left_color;
                var right_color;

                var colors;
                switch (colorsMode) {
                    case 'colorful':
                        colors = {
                            'voltage': '#0080ff',
                            'current': '#e50000',
                            'current-m': '#e50000',
                            'power': '#eabe24',
                            'temperature': '#417200',
                            'accumulated_current': '#a824ea',
                            'accumulated_power': '#014d98',
                            'resistance': '#6cc972',
                            'fallback': '#373737'
                        };
                        left_color = colors.hasOwnProperty(left_axis) ? colors[left_axis] : colors['fallback'];
                        right_color = colors.hasOwnProperty(right_axis) ? colors[right_axis] : colors['fallback'];
                        break;

                    case 'midnight':
                        colors = {
                            'voltage': '#5489bf',
                            'current': '#c83c3c',
                            'current-m': '#c83c3c',
                            'power': '#eabe24',
                            'temperature': '#549100',
                            'accumulated_current': '#9c78bc',
                            'accumulated_power': '#997b18',
                            'resistance': '#56a05a',
                            'fallback': '#373737'
                        };
                        left_color = colors.hasOwnProperty(left_axis) ? colors[left_axis] : colors['fallback'];
                        right_color = colors.hasOwnProperty(right_axis) ? colors[right_axis] : colors['fallback'];
                        break;

                    default:
                        left_color = '#0080ff';
                        right_color = '#e50000';
                }

                var unit = function (name) {
                    var matches = name.match(/\(([^)]+)\)/i);
                    if (matches) {
                        return matches[1];
                    }
                    return null;
                };
                var left_unit = unit(left_name);
                var right_unit = unit(right_name);

                var url = graph.attr('data-url');
                url += '?session=' + session;
                url += '&left_axis=' + left_axis;
                url += '&right_axis=' + right_axis;
                url += '&colors=' + colorsMode;

                $.get(url, function (data) {
                    var xAxisTextColor = null;
                    var axisLineColor = null;
                    var cursorColor = null;
                    switch (ntdrt.theme) {
                        case 'midnight':
                            xAxisTextColor = '#c8c8c8';
                            axisLineColor = '#464646';
                            cursorColor = '#65ff00';
                            break;

                        case 'dark':
                            xAxisTextColor = '#c8c8c8';
                            axisLineColor = '#464646';
                            cursorColor = '#c8c8c8';
                            break;
                    }

                    var root = chartRoot = am5.Root.new(graph[0]);
                    var chart = am5xy.XYChart.new(root, {});
                    root.container.children.push(chart);
                    root.numberFormatter.set('numberFormat', "####.####");

                    var xAxis = chart.xAxes.push(
                        am5xy.DateAxis.new(root, {
                            renderer: am5xy.AxisRendererX.new(root, {}),
                            groupData: true,
                            groupCount: 10000,
                            baseInterval: {
                                timeUnit: 'second',
                                count: 1
                            },
                        })
                    );
                    if (xAxisTextColor) {
                        xAxis.get('renderer').labels.template.setAll({
                            fill: xAxisTextColor
                        });
                    }
                    if (axisLineColor) {
                        xAxis.get('renderer').grid.template.setAll({
                            stroke: axisLineColor
                        });
                    }
                    var xLabel = xAxis.children.push(
                        am5.Label.new(root, {
                            text: 'Time',
                            x: am5.p50,
                            centerX: am5.p50
                        })
                    );
                    if (xAxisTextColor) {
                        xLabel.setAll({
                            fill: xAxisTextColor
                        });
                    }

                    var yLeftAxis = chart.yAxes.push(
                        am5xy.ValueAxis.new(root, {
                            renderer: am5xy.AxisRendererY.new(root, {}),
                            numberFormat: '####.## \' ' + left_unit + '\'',
                            min: 0
                        })
                    );
                    yLeftAxis.get('renderer').labels.template.setAll({
                        fill: left_color,
                        fontWeight: 700
                    });
                    if (axisLineColor) {
                        yLeftAxis.get('renderer').grid.template.setAll({
                            stroke: axisLineColor
                        });
                    }
                    yLeftAxis.children.push(
                        am5.Label.new(root, {
                            text: left_name,
                            rotation: -90,
                            y: am5.p50,
                            x: -30,
                            centerX: am5.p50,
                            fill: left_color,
                            fontWeight: 700
                        })
                    );
                    var leftTooltip = am5.Tooltip.new(root, {
                        getFillFromSprite: false,
                        autoTextColor: false,
                        labelText: '{valueY} ' + left_unit
                    });
                    leftTooltip.get('background').setAll({
                        fill: left_color,
                    });
                    leftTooltip.label.setAll({
                        fill: '#fff'
                    });
                    var leftSeries = self.chartLeft = chart.series.push(
                        am5xy.LineSeries.new(root, {
                            xAxis: xAxis,
                            yAxis: yLeftAxis,
                            valueXField: 'date',
                            valueYField: 'left',
                            stroke: left_color,
                            tooltip: leftTooltip
                        })
                    );
                    leftSeries.strokes.template.setAll({
                        strokeWidth: 2
                    });
                    leftSeries.data.setAll(data);

                    var yRightAxis = chart.yAxes.push(
                        am5xy.ValueAxis.new(root, {
                            renderer: am5xy.AxisRendererY.new(root, {
                                opposite: true
                            }),
                            numberFormat: '####.## \' ' + right_unit + '\'',
                            min: 0
                        })
                    );
                    yRightAxis.get('renderer').labels.template.setAll({
                        fill: right_color,
                        fontWeight: 700
                    });
                    if (axisLineColor) {
                        yRightAxis.get('renderer').grid.template.setAll({
                            stroke: axisLineColor
                        });
                    }
                    yRightAxis.children.push(
                        am5.Label.new(root, {
                            text: right_name,
                            rotation: 90,
                            y: am5.p50,
                            centerX: am5.p50,
                            fill: right_color,
                            fontWeight: 700
                        })
                    );
                    var rightTooltip = am5.Tooltip.new(root, {
                        getFillFromSprite: false,
                        autoTextColor: false,
                        labelText: '{valueY} ' + right_unit
                    });
                    rightTooltip.get('background').setAll({
                        fill: right_color,
                    });
                    rightTooltip.label.setAll({
                        fill: '#fff'
                    });
                    var rightSeries = self.chartRight = chart.series.push(
                        am5xy.LineSeries.new(root, {
                            xAxis: xAxis,
                            yAxis: yRightAxis,
                            valueXField: 'date',
                            valueYField: 'right',
                            stroke: right_color,
                            tooltip: rightTooltip
                        })
                    );
                    rightSeries.strokes.template.setAll({
                        strokeWidth: 2
                    });
                    rightSeries.data.setAll(data);

                    var cursor = am5xy.XYCursor.new(root, {
                        behavior: 'zoomX'
                    });
                    if (cursorColor) {
                        cursor.lineX.setAll({
                            stroke: cursorColor
                        });
                        cursor.lineY.setAll({
                            stroke: cursorColor
                        });
                    }
                    chart.set('cursor', cursor);

                    var timeout = null;
                    var onFrameEnded = function () {
                        if (timeout) {
                            clearTimeout(timeout);
                        }
                        timeout = setTimeout(function () {
                            root.events.off('frameended', onFrameEnded);
                            graph.parent().find('.loading').hide();
                        }, 100)
                    };
                    root.events.on('frameended', onFrameEnded);
                });
            };

            create();

            $(document).on('submit', '#graph-settings', function (e) {
                create();
                return false;
            });
        }
    },

    logScroll: function (delay) {
        var target = $('#log');
        target.animate({scrollTop: target.prop("scrollHeight")}, delay);
    },

    logResize: function () {
        var target = $('#log');
        var height = $(window).height();
        height -= $('body').height();
        height += target.height();
        target.css('height', height + 'px')
    },

    disable: function (value) {
        $('#connect select').prop('disabled', value);
        $('#connect input').prop('disabled', value);
    },

    register: function () {
        $(function () {
            ntdrt.application.init();
        });
    }
};

ntdrt.application.register();
