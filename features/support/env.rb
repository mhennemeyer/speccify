require 'rubygems'
require 'tempfile'
require 'test/unit'
# may cucumber be used without rspec?
# require File.dirname(__FILE__) + "/../../lib/midi_spec.rb"
World do |world|
  world.extend(Test::Unit::Assertions)
  world
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
