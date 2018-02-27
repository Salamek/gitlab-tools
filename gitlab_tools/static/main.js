
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

    $('.check-signature').each(function(){
        var $input = $(this);
        var $form = $input.closest('form');
        var url = $input.data('fingerprint-url');
        var add_url = $input.data('fingerprint-add-url');
        var redirect_url = $input.data('fingerprint-redirect-url');
        $form.submit(function(e){
            e.preventDefault();

            var data = $input.val();
            if (!data)
            {
                alert('No data');
                return;
            }

            $.ajax({
                type: "POST",
                dataType: 'json',
                contentType: 'application/json',
                url: url,
                data: JSON.stringify({
                    'url': $input.val().trim()
                }),
                success: function(data){
                    if (data.found)
                    {
                        $form.unbind().submit();
                    }
                    else
                    {
                        prompt_result = prompt(
                        "The authenticity of host "+ data.hostname +" can't be established.\n" +
                        "RSA key fingerprint is MD5:" + data.rsa_md5_fingerprint + ".\n" +
                        "RSA key fingerprint is SHA256:" + data.rsa_sha256_fingerprint + ".\n" +
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
                                   $form.unbind().submit();
                                },
                                error: function(e){
                                    alert('We are sorry but request failed. Check console for more information');
                                    console.log(e);
                                }
                            });
                        }
                        else
                        {
                            return;
                        }
                    }
                },
                error: function(e){
                    alert('We are sorry but request failed. Check console for more information');
                    console.log(e);
                }
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