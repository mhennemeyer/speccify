# MidiSpec
#
# A testing framework like minispec that provides more rspec like functionality.
#
#  Features:
#
#  * fast.
#  * nested contexts with 'chained' before and after blocks.
#  * 'obj.should matcher' syntax.
#  * provides an easy way to define matchers. Even complex ones that 
#    are taking args and may receive messages.
#  * 1.9 compatible.
#  * mock framework agnostic
#
# There are several examples coming after the framework definition
#
# Based on Ryan Davis' MiniTest/Spec

require "rubygems"
require "minitest/unit"
MiniTest::Unit.autorun

module MidiSpec
  module ExampleGroupClassMethods
    def desc=(desc)
      @desc = desc
    end

    def desc
      @desc || ""
    end

    def setup_proc=(proc)
      @setup_proc = proc
    end

    def setup_proc
      @setup_proc || lambda {}
    end

    def teardown_proc=(proc)
      @teardown_proc = proc
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
      if defined?(Rails)
        if self.name =~ /^(.*Controller)Test/
          super_class = RailsControllerExampleGroup
        else
          super_class = RailsExampleGroup
        end
      else
        super_class = MidiSpec::ExampleGroup
      end
      cls = Class.new(super_class)
      Object.const_set self.name + desc.to_s.split(/\W+/).map { |s| s.capitalize }.join, cls
      cls.setup_proc = self.setup_proc
      cls.teardown_proc = self.teardown_proc
      cls.desc = self.desc + " " + desc
      if defined?(Rails)
        self.name =~ /^(.*Controller)Test/ ? cls.tests($1.constantize) : nil
      end
      cls.class_eval(&block)
    end
    
    def it desc, &block
      self.before {}
      define_method "test_#{desc.gsub(/\W+/, '_').downcase}", &block
      self.after {}
    end
  end
  
  module ExampleGroupMethods
    def initialize name
      super
      $current_spec = self
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
  
  class RailsModelExampleGroup < defined?(Rails) ? ::ActiveSupport::TestCase : MiniTest::Unit::TestCase
    extend ExampleGroupClassMethods
    include ExampleGroupMethods
  end
  
  # Redefine MiniTest::Unit's way of formatting failuremessages
  # Only the line between the +++ is added. Nothing else is touched.
  MiniTest::Unit.class_eval do 
    def puke klass, meth, e
      e = case e
          when MiniTest::Skip then
            @skips += 1
            "Skipped:\n#{meth}(#{klass}) [#{location e}]:\n#{e.message}\n"
          when MiniTest::Assertion then
            @failures += 1
            # +++
            return "Failure:\n #{klass.desc} #{meth.gsub(/^test_/,"").split("_").join(" ")} \n#{e.message}\n" unless klass.superclass.to_s == "MiniTest::Unit::TestCase"
            # +++
            
            "Failure:\n#{meth}(#{klass}) [#{location e}]:\n#{e.message}\n"
          else
            @errors += 1
            bt = MiniTest::filter_backtrace(e.backtrace).join("\n    ")
            
            # +++
            return "Error:\n #{klass.desc} #{meth.gsub(/^test_/,"").split("_").join(" ")} \n#{e.message}\n    #{bt}\n" if klass.superclass.to_s == "MidiSpec::ExampleGroup"
            # +++
            
            "Error:\n#{meth}(#{klass}):\n#{e.class}: #{e.message}\n    #{bt}\n"
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
          define_method(operator.to_sym) do |actual|
            print_given  = (@given == nil) ? "nil" : @given
            print_actual = (actual == nil) ? "nil" : actual
            if type 
              msg = """
                    Expected: #{print_actual}
                         got: #{print_given} 
             comparison with: #{operator}
                    """ 
            else
              msg = """
                    Expected not: #{print_actual}
                         but got: #{print_given} 
                 comparison with: #{operator}
                    """
            end
            comparison = type == @given.send(operator.to_sym,actual)
            $current_spec.assert(comparison, msg  + "\n" + "(" + loc + ")")
          end
        end
      end

      return Class.new(&body).new(given)
    end
  end

  Object.class_eval do
    def should matcher = nil
      if matcher
        $current_spec.assert(matcher.matches?(self),matcher.positive_msg + "\n" + "(" + caller[0] + ")")
      else
        OperatorMatcherProxy.create(self,caller[0])
      end
    end

    def should_not matcher = nil
      if matcher 
        $current_spec.assert(!matcher.matches?(self),matcher.negative_msg + "\n" + "(" + caller[0] + ")")
      else 
        OperatorMatcherProxy.create(self,caller[0], false)
      end
    end
  end
  
  
  module Extension
    def describe *args, &block
      cnst, desc = args
      if defined?(Rails)
        if cnst.to_s =~ /Controller$/
          super_class = RailsControllerExampleGroup
        else
          super_class = RailsExampleGroup
        end
      else
        super_class = MidiSpec::ExampleGroup
      end  
      name = cnst.instance_of?(String) ? (cnst.to_s + "Test").to_s.split(/\W+/).map { |s| s.capitalize }.join : cnst.to_s + "Test"
      cls = Class.new(super_class)
      Object.const_set name, cls
      cls.desc = desc || cnst.to_s
      cls.class_eval(&block)
    end
    private :describe
    
    def def_matcher(matcher_name, &block)
      self.class.send :define_method, matcher_name do |*args|
        match_block = lambda do |actual, matcher|
          block.call(actual, matcher, args)
        end
        body = lambda do |klass|
          attr_accessor :positive_msg, :negative_msg, :fn
          def initialize match_block
            @match_block = match_block
            @positive_msg = "Expected "
            @negative_msg = "Unexpected "
          end
          
          def method_missing id, *args, &block
            require 'ostruct'
            self.fn = OpenStruct.new( "name" => id, "args" => args, "block" => block ) 
            self
          end

          def matches? given
            @match_block.call(given, self)
          end
        end
        Class.new(&body).new(match_block)
      end
    end
  end # Extension
end # 
include MidiSpec::Extension

#
### Some examples:
#

# Minimal:
describe "ExampleGroup" do
  it "Example" do
    1.should == 1
  end
end


# With a minimal matcher:
def_matcher :be_nil do |given, matcher, args|
  matcher.positive_msg = "expected #{given} to be nil"
  matcher.negative_msg = "expected not nil"
  given == nil
end

describe "Be nil matcher" do
  it "should pass if given is nil" do
    nil.should be_nil
  end
end


# Nested ExampleGroups
describe "first level" do
  
  before do
    $first_level_before ||= 0
    $first_level_before += 1
  end
  
  after do
    $first_level_after ||= 0
    $first_level_after += 1
  end
  
  it "example in first level" do
    $first_level_after.should be_nil
    $first_level_before.should == 1
  end

  describe "second level" do

    before do
      $second_level_before ||= 0
      $second_level_before += 1
    end
    
    after do
      $second_level_after ||= 0
      $second_level_after += 1
    end
    
    it "example in second level" do
      $second_level_after.should == nil
      $first_level_after.should == 1
      $first_level_before.should == 2
      $second_level_before.should == 1
    end
    
    describe "third level" do
      it "second_level_after should have been called now" do
        $second_level_after.should == 1
      end
      
      describe "four" do
        before do
          @var = 1
        end
        describe "Variable defined in parent block " do
          it "should be available without calling before" do
            @var.should_not == nil
          end
        end
      end
    end
  end
end


# A change alike matcher
def_matcher :change do |given, matcher, args|
  raise "callseq: change(lambda {'something here'})" unless Proc === (prok = args[0])
  before = prok.call
  given.call
  before != prok.call
end

describe "Change matcher" do
  before do
    @var = 1
  end
  
  it "should pass if actual was actually changed by given" do
    lambda {@var = 2}.should change(lambda {@var})
  end
  
  it "should not pass if actual was not changed by given" do
    lambda { }.should_not change(lambda {@var})
  end
end