require 'rubygems'
require 'tempfile'
require 'spec'
# todo use midispec!!!

def smart_match(string_or_regexp)
  simple_matcher string_or_regexp do |given|
    if Regexp === string_or_regexp
      (given =~ string_or_regexp) ? true : false
    else 
      (given.index string_or_regexp.to_s) ? true : false
    end
  end
end

def ruby(args, stderr=nil)
  config       = ::Config::CONFIG
  interpreter  = File::join(config['bindir'], config['ruby_install_name']) + config['EXEEXT']
  cmd = "#{interpreter} #{args}"
  cmd << " 2> #{stderr}" unless stderr.nil?
  `#{cmd}`
end

def ruby19(args, stderr=nil)
  cmd = "ruby1.9 #{args}"
  cmd << " 2> #{stderr}" unless stderr.nil?
  `#{cmd}`
end
