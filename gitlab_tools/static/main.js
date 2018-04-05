
$(function () {
    $(document).on('click', '[data-toggle="lightbox"]', function(event) {
        event.preventDefault();
        $(this).ekkoLightbox();
    });

    $('.api-test').click(function(){
        var url = $(this).data('url');

        var $container = $(this).next('.jumbotron');
        if (!$container.length)
        {
            $container = $('<pre class="jumbotron">');
            $(this).after($container);
        }

        $.ajax({
            type: 'GET',
            url: url,
            success: function(data){
                $container.html(JSON.stringify(data, null, 2));
            },
            error: function() {
                $container.html('<div class="alert alert-danger">Failed</div>');
            }
        });
    });

    var processAjaxError = function($xhr){
        var data = $xhr.responseJSON;
        if (data && 'message' in data)
        {
            alert(data.message);
        }
        else
        {
            alert('We are sorry but request failed. Check console for more information');
            console.log(e);
        }
    };

    var checkUrlFingerprint = function(check_url, add_url, fingerprint_url, success_callback)
    {
        $.ajax({
            type: "POST",
            dataType: 'json',
            contentType: 'application/json',
            url: fingerprint_url,
            data: JSON.stringify({
                'url': check_url
            }),
            success: function(data){
                if (data.found)
                {
                    success_callback();
                }
                else
                {
                    prompt_result = prompt(
                    "The authenticity of host "+ data.hostname +" can't be established.\n" +
                    "MD5 Key fingerprint is:" + data.md5_fingerprint + ".\n" +
                    "SHA256 Key fingerprint is:" + data.sha256_fingerprint + ".\n" +
                    "Are you sure you want to add this fingerprint (yes/no)?"
                    );

                    if (prompt_result == "yes")
                    {
                        $.ajax({
                            type: "POST",
                            dataType: 'json',
                            contentType: 'application/json',
                            url: add_url,
                            data: JSON.stringify(data),
                            success: function(data){
                               success_callback();
                            },
                            error: processAjaxError
                        });
                    }
                    else
                    {
                        return;
                    }
                }
            },
            error: processAjaxError
        });
    };

    $('.check-signature').each(function(){
        var $input = $(this);
        var $form = $input.closest('form');
        var fingerprint_url = $input.data('fingerprint-url');
        var gitlab_url = $input.data('gitlab-url');
        var add_url = $input.data('fingerprint-add-url');
        $form.submit(function(e){
            e.preventDefault();

            var data = $input.val();
            if (!data)
            {
                alert('No data');
                return;
            }

            checkUrlFingerprint(gitlab_url, add_url, fingerprint_url, function(){
                checkUrlFingerprint($input.val().trim(), add_url, fingerprint_url, function(){
                    $form.unbind().submit();
                });
            });
        });
    });

    $('.confirm').click(function(e){
        var message = $(this).data('confirm-message');
        if (!confirm(message))
        {
            e.preventDefault();
        }
    });

    $('.date').each(function(){
        $(this).datetimepicker({
            format: 'DD.MM.YYYY HH:mm'
        });
    });

    $('[data-toggle="popover"]').popover();
    $('.has-error .form-control').first().focus();

    /**
   * Allow anchored tabs
   */
    //Support for urling tabs
    var url = document.location.toString();
    if (url.match('#')) {
        $('.nav-tabs a[href=#'+url.split('#')[1]+']').tab('show') ;
    }

    // Change hash for page-reload
    $('.nav-tabs a').on('shown.bs.tab', function (e) {
        window.location.hash = e.target.hash;
    });
 });