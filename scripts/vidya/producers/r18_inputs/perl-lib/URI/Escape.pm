package URI::Escape;
use strict;
use warnings;
use Exporter 'import';
our @EXPORT = qw(uri_unescape);
sub uri_unescape {
    my ($text) = @_;
    $text =~ s/%([0-9A-Fa-f]{2})/chr(hex($1))/eg;
    return $text;
}
1;
