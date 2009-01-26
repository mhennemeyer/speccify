require "rubygems"
require "minitest/unit"
MiniTest::Unit.autorun

module MidiSpec
  module ExampleGroupClassMethods
    attr_accessor :desc, :setup_proc, :teardown_proc
    @desc ||= ""
    
    def setup_proc
      @setup_proc || lambda {}
    end
    
    def teardown_proc
      @teardown_proc || lambda {}
    end

    def before(type = :each, &block)
      raise "unsupported before type: #{type}" unless type == :each
      passed_through_setup = self.setup_proc
      self.setup_proc = lambda { instance_eval(&passed_through_setup);instance_eval(&block) }
      define_method :setup, &self.setup_proc
    end

    def after(type = :each, &block)
      raise "unsupported after type: #{type}" unless type == :each
      passed_through_teardown = self.teardown_proc
      self.teardown_proc = lambda {instance_eval(&block);instance_eval(&passed_through_teardown) }
      define_method :teardown, &self.teardown_proc
    end
    
    def describe desc, &block
      cls = Class.new(MidiSpec::Functions::determine_superclass(self.name))
      Object.const_set self.name + desc.to_s.split(/\W+/).map { |s| s.capitalize }.join, cls
      cls.setup_proc = self.setup_proc
      cls.teardown_proc = self.teardown_proc
      cls.desc = self.desc + " " + desc
      if defined?(Rails)
        self.name =~ /^(.*Controller)Test/ ? cls.tests($1.constantize) : nil
      end
      p cls
      cls.class_eval(&block)
    end
    
    def it desc, &block
      self.before {}
      define_method "test_#{desc.gsub(/\W+/, '_').downcase}", &block if block_given?
      self.after {}
    end
  end
  
  module ExampleGroupMethods
    def initialize name
      super
      $current_spec = self
    end
  end
  
  module Functions
    def self.determine_superclass(cnst)
      if defined?(Rails)
        sc = (cnst.to_s =~ /Controller/) ?  MidiSpec::RailsControllerExampleGroup : MidiSpec::RailsExampleGroup
      else
        sc = MidiSpec::ExampleGroup
      end
      sc
    end
    
    def self.determine_class_name(name)
      name.to_s.split(/\W+/).map { |s| s[0..0].upcase + s[1..-1] }.join 
    end
    
    def self.message(expected, actual, op, location) 
            """
              Expected: #{expected.to_s}
                   got: #{actual.to_s} 
       comparison with: #{op.to_s}
              location: (#{location})
            """
    end
  end
  
  class ExampleGroup < MiniTest::Unit::TestCase
    extend ExampleGroupClassMethods
    include ExampleGroupMethods
  end
  
  class RailsControllerExampleGroup < defined?(Rails) ? ::ActionController::TestCase : MiniTest::Unit::TestCase
    extend ExampleGroupClassMethods
    include ExampleGroupMethods
  end
  
  class RailsExampleGroup < defined?(Rails) ? ::ActiveSupport::TestCase : MiniTest::Unit::TestCase
    extend ExampleGroupClassMethods
    include ExampleGroupMethods
  end
  
  # Redefine MiniTest::Unit's way of formatting failuremessages
  MiniTest::Unit.class_eval do 
    def puke klass, meth, e
      e = case e
          when MiniTest::Skip then
            @skips += 1
            "Skipped:\n#{meth}(#{klass}) [#{location e}]:\n#{e.message}\n"
          when MiniTest::Assertion then
            @failures += 1
            unless klass.superclass.to_s == "MiniTest::Unit::TestCase"
              "Failure:\n #{klass.desc} #{meth.gsub(/^test_/,"").split("_").join(" ")} \n#{e.message}\n" 
            else
              "Failure:\n#{meth}(#{klass}) [#{location e}]:\n#{e.message}\n"
            end
          else
            @errors += 1
            bt = MiniTest::filter_backtrace(e.backtrace).join("\n    ")
            unless klass.superclass.to_s == "MiniTest::Unit::TestCase"
              "Error:\n #{klass.desc} #{meth.gsub(/^test_/,"").split("_").join(" ")} \n#{e.message}\n #{bt}\n" 
            else
              "Error:\n#{meth}(#{klass}):\n#{e.class}: #{e.message}\n    #{bt}\n"
            end
          end
      @report << e
      e[0, 1]
    end
  end

  class OperatorMatcherProxy
    def self.create given, loc, type = true
      body = lambda do |klass|
        define_method(:initialize) do |given|
          @given = given
        end

        ['==', '===', '=~', '>', '>=', '<', '<='].each do |operator|
          define_method(operator) do |actual|
            print_given  = (@given == nil) ? "nil" : @given
            print_actual = (type ? "" : "not ") + (actual.nil? ? "nil" : actual.to_s)
            msg = MidiSpec::Functions::message(print_actual, print_given, operator, loc) 
            $current_spec.assert(type == @given.send(operator,actual), msg)
          end
        end
      end

      return Class.new(&body).new(given)
    end
  end

  Object.class_eval do
    def should matcher = nil
      if matcher
        matcher.loc = caller[0]
        $current_spec.assert(matcher.matches?(self), matcher.positive_msg)
      else
        OperatorMatcherProxy.create(self,caller[0])
      end
    end

    def should_not matcher = nil
      if matcher
        matcher.loc = caller[0]
        $current_spec.assert(!matcher.matches?(self), matcher.negative_msg)
      else 
        OperatorMatcherProxy.create(self,caller[0], false)
      end
    end
  end
  
  
  module Extension
    def describe *args, &block
      cnst, desc = args
      p cnst
      cls = Class.new(MidiSpec::Functions::determine_superclass(cnst))
      Object.const_set MidiSpec::Functions::determine_class_name(cnst.to_s + "Test"), cls
      p cls
      cls.desc = desc || cnst.to_s
      cls.class_eval(&block)
    end
    private :describe
    
    def def_matcher(matcher_name, &block)
      name = matcher_name.to_s
      self.class.send :define_method, matcher_name do |*args|
        match_block = lambda do |actual, matcher|
          block.call(actual, matcher, args)
        end
        body = lambda do |klass|
          @matcher_name = matcher_name.to_s
          def self.matcher_name
            @matcher_name
          end
          
          attr_accessor :positive_msg, :negative_msg, :fn, :loc
          def initialize match_block
            @match_block = match_block
          end
          
          def method_missing id, *args, &block
            require 'ostruct'
            (self.fn ||= []) << OpenStruct.new( "name" => id, "args" => args, "block" => block ) 
            self
          end

          def matches? given
            @positive_msg ||= MidiSpec::Functions::message("#{given} should #{self.class.matcher_name}", "no match", self.class.matcher_name , self.loc || "") 
            @negative_msg ||= MidiSpec::Functions::message("#{given} should not #{self.class.matcher_name}", "match", self.class.matcher_name , self.loc || "")
            @match_block.call(given, self)
          end
        end
        Class.new(&body).new(match_block)
      end
    end
  end # Extension
end # MidiSpec
include MidiSpec::Extension
