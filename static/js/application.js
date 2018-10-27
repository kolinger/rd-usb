var ntdrt = ntdrt || {};

ntdrt.application = {
    init: function () {
        var self = ntdrt.application;

        var socket = io.connect('http://' + document.domain + ':' + location.port);
        socket.on('connect', function () {
        });

        socket.on('connecting', function () {
            $('#status').text('Connecting');
            self.disable(true);
            $('#connect button').text('Disconnect');
        });

        socket.on('connected', function () {
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

        $(document).on('submit', '#connect', function (e) {
            var form = $(e.target);
            var input = form.find('[name="port"]');
            if (input.is(':disabled')) {
                socket.emit('close');
            } else {
                var data = {
                    port: input.val(),
                    rate: form.find('[name="rate"]').val(),
                    name: form.find('[name="name"]').val()
                };
                data = JSON.stringify(data);
                socket.emit('open', data);
            }
            return false;
        });

        if ($('#log').length) {
            socket.on('log', function (message) {
                $('#log').append(message);
                self.logScroll(500);
            });

            $(window).on('resize', self.logResize);
            self.logResize();
            self.logScroll(0);
        }

        var chart = null;
        var left_axis;
        var right_axis;
        var graph = $('#graph');
        if (graph.length) {
            var create = function () {
                if (chart) {
                    chart.destroy();
                }
                var name = $('select[name="name"]').val();

                left_axis = $('select[name="left_axis"]').val();
                var left_name = $('#graph-settings option[value="' + left_axis + '"]').first().text();
                right_axis = $('select[name="right_axis"]').val();
                var right_name = $('#graph-settings option[value="' + right_axis + '"]').first().text();

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
                url += '?name=' + name;
                url += '&left_axis=' + left_axis;
                url += '&right_axis=' + right_axis;

                $.get(url, function (data) {
                    chart = new Chart(graph[0], {
                        type: 'line',
                        data: {
                            datasets: [{
                                label: left_name,
                                data: data['left']['data'],
                                yAxisID: 'left',
                                borderColor: [
                                    'rgba(229, 0, 0, 1)',
                                ],
                                borderWidth: 2,
                                backgroundColor: [
                                    'rgba(229, 0, 0, 0.5)',
                                ],
                                fill: false,
                            }, {
                                label: right_name,
                                data: data['right']['data'],
                                yAxisID: 'right',
                                borderColor: [
                                    'rgba(0, 128, 255, 1)',
                                ],
                                borderWidth: 2,
                                backgroundColor: [
                                    'rgba(0, 128, 255, 0.5)',
                                ],
                                fill: false
                            }]
                        },
                        options: {
                            elements: {
                                point: {
                                    radius: 0
                                }
                            },
                            tooltips: {
                                mode: 'index',
                                intersect: false,
                                callbacks: {
                                    labelColor: function(tooltipItem, chart) {
                                        var data = chart.config.data.datasets[tooltipItem.datasetIndex];
                                        return {
                                            backgroundColor: data['borderColor'][0]
                                        }
                                    },
                                }
                            },
                            hover: {
                                mode: 'index',
                                intersect: false
                            },
                            scales: {
                                xAxes: [{
                                    type: 'time',
                                    time: {
                                        displayFormats: {
                                            millisecond: 'HH:mm:ss',
                                            second: 'HH:mm:ss',
                                            minute: 'HH:mm',
                                            hour: 'HH:mm',
                                            day: 'YYYY-MM-DD HH:mm',
                                            week: 'YYYY-MM-DD',
                                            month: 'YYYY-MM-DD',
                                            quarter: 'YYYY-MM-DD',
                                            year: 'YYYY-MM-DD',
                                        },
                                        tooltipFormat: 'YYYY-MM-DD HH:mm:ss'
                                    }
                                }],
                                yAxes: [
                                    {
                                        id: 'left',
                                        type: 'linear',
                                        position: 'left',
                                        ticks: {
                                            min: 0,
                                            callback: function (value, index, values) {
                                                if (!left_unit) {
                                                    return value;
                                                }
                                                return value + ' ' + left_unit;
                                            }
                                        }
                                    },
                                    {
                                        id: 'right',
                                        type: 'linear',
                                        position: 'right',
                                        ticks: {
                                            min: 0,
                                            callback: function (value, index, values) {
                                                if (!right_unit) {
                                                    return value;
                                                }
                                                return value + ' ' + right_unit;
                                            }
                                        }
                                    }
                                ]
                            }
                        }
                    });
                });
            };

            create();

            $(document).on('submit', '#graph-settings', function (e) {
                create();
                return false;
            });
        }

        var current = $('#current');
        if (current.length) {
            socket.on('update', function (message) {
                var data = JSON.parse(message);
                var counter = 0;
                current.find('td').each(function () {
                    $(this).text(data['table'][counter]);
                    counter++;
                });

                if (chart && left_axis && right_axis) {
                    if (data['graph'].hasOwnProperty(left_axis) && data['graph'].hasOwnProperty(right_axis)) {
                        chart.data.datasets[0].data.push({
                            t: data['graph']['timestamp'],
                            y: data['graph'][left_axis],
                        });
                        chart.data.datasets[1].data.push({
                            t: data['graph']['timestamp'],
                            y: data['graph'][right_axis],
                        });
                        try {
                            chart.update();
                        } catch (e) {
                            // ignore
                        }
                    }
                }
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
